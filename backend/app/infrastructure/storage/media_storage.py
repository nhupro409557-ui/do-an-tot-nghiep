from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlparse

from app.config import settings


class StorageConfigurationError(RuntimeError):
    pass


class StorageReadOnlyError(RuntimeError):
    pass


class MediaStorage:
    ALLOWED_DRIVERS = {"auto", "local", "bundled", "s3"}

    def __init__(self, storage_settings=settings):
        self.settings = storage_settings
        configured_driver = str(storage_settings.media_storage_driver).strip().lower()
        if configured_driver not in self.ALLOWED_DRIVERS:
            raise StorageConfigurationError(
                "MEDIA_STORAGE_DRIVER chỉ chấp nhận auto, local, bundled hoặc s3."
            )

        s3_ready = self._has_complete_s3_configuration()
        self.driver = "s3" if configured_driver == "auto" and s3_ready else configured_driver
        if self.driver == "auto":
            self.driver = "local"
        if self.driver == "s3" and not s3_ready:
            raise StorageConfigurationError(
                "Chế độ S3 cần đủ S3_BUCKET, S3_ACCESS_KEY_ID, "
                "S3_SECRET_ACCESS_KEY và S3_PUBLIC_BASE_URL."
            )

        public_path = str(storage_settings.media_public_path or "/media").strip()
        self.public_path = f"/{public_path.strip('/')}"

    @property
    def supports_runtime_upload(self) -> bool:
        return self.driver in {"local", "s3"}

    def _has_complete_s3_configuration(self) -> bool:
        return all(
            [
                self.settings.s3_bucket,
                self.settings.s3_access_key_id,
                self.settings.s3_secret_access_key,
                self.settings.s3_public_base_url,
            ]
        )

    def _normalize_file_key(self, file_key: str) -> str:
        normalized = str(file_key or "").strip().replace("\\", "/")
        path = PurePosixPath(normalized)
        if not normalized or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError("Đường dẫn tệp media không hợp lệ.")
        return path.as_posix()

    def resolve_local_path(self, file_key: str) -> Path:
        normalized = self._normalize_file_key(file_key)
        root = Path(self.settings.media_local_directory).resolve()
        target = (root / Path(normalized)).resolve()
        if not target.is_relative_to(root):
            raise ValueError("Đường dẫn tệp media không hợp lệ.")
        return target

    def public_url(self, file_key: str, base_url: str) -> str:
        normalized = self._normalize_file_key(file_key)
        encoded_key = quote(normalized, safe="/")
        return f"{base_url.rstrip('/')}{self.public_path}/{encoded_key}"

    def external_url(self, file_key: str) -> str:
        if self.driver != "s3":
            raise StorageConfigurationError("Chỉ storage S3 mới có URL ngoài trực tiếp.")
        normalized = self._normalize_file_key(file_key)
        return f"{self.settings.s3_public_base_url.rstrip('/')}/{quote(normalized, safe='/')}"

    def file_key_from_url(self, url: str) -> str | None:
        parsed_url = urlparse(str(url or ""))
        path = unquote(parsed_url.path).replace("\\", "/")
        prefixes = [f"{self.public_path}/", "/uploads/"]
        for prefix in prefixes:
            if path.startswith(prefix):
                try:
                    return self._normalize_file_key(path[len(prefix):])
                except ValueError:
                    return None
        if self.settings.s3_public_base_url:
            parsed_base = urlparse(self.settings.s3_public_base_url.rstrip("/"))
            base_path = parsed_base.path.rstrip("/")
            if (
                parsed_url.scheme == parsed_base.scheme
                and parsed_url.netloc == parsed_base.netloc
                and path.startswith(f"{base_path}/")
            ):
                try:
                    return self._normalize_file_key(path[len(base_path) + 1:])
                except ValueError:
                    return None
        return None

    def normalize_storage_key(self, storage_key: str) -> str:
        normalized = str(storage_key or "").strip().replace("\\", "/").lstrip("/")
        if normalized.startswith("uploads/"):
            normalized = normalized[len("uploads/"):]
        return self._normalize_file_key(normalized)

    def write_bytes(self, file_key: str, data: bytes, content_type: str) -> None:
        normalized = self._normalize_file_key(file_key)
        if self.driver == "bundled":
            raise StorageReadOnlyError(
                "Kho bundled chỉ đọc; hãy thêm tệp vào Git rồi triển khai lại."
            )
        if self.driver == "s3":
            self._s3_client().put_object(
                Bucket=self.settings.s3_bucket,
                Key=normalized,
                Body=data,
                ContentType=content_type,
            )
            return
        target = self.resolve_local_path(normalized)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def delete(self, file_key: str) -> None:
        normalized = self.normalize_storage_key(file_key)
        if self.driver == "bundled":
            raise StorageReadOnlyError("Kho bundled không cho phép xóa tệp khi đang chạy.")
        if self.driver == "s3":
            self._s3_client().delete_object(Bucket=self.settings.s3_bucket, Key=normalized)
            return
        self.resolve_local_path(normalized).unlink(missing_ok=True)

    def count(self, prefix: str) -> int:
        normalized_prefix = self._normalize_file_key(prefix).rstrip("/") + "/"
        if self.driver == "s3":
            client = self._s3_client()
            continuation_token = None
            total = 0
            while True:
                params = {"Bucket": self.settings.s3_bucket, "Prefix": normalized_prefix}
                if continuation_token:
                    params["ContinuationToken"] = continuation_token
                response = client.list_objects_v2(**params)
                total += int(response.get("KeyCount", len(response.get("Contents", []))))
                if not response.get("IsTruncated"):
                    return total
                continuation_token = response.get("NextContinuationToken")
        directory = self.resolve_local_path(normalized_prefix.rstrip("/"))
        if not directory.exists():
            return 0
        return sum(1 for path in directory.iterdir() if path.is_file())

    def create_presigned_put_url(self, file_key: str, content_type: str) -> str:
        if self.driver != "s3":
            raise StorageConfigurationError("Presigned URL chỉ được tạo cho storage S3.")
        normalized = self._normalize_file_key(file_key)
        return self._s3_client().generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.settings.s3_bucket,
                "Key": normalized,
                "ContentType": content_type,
            },
            ExpiresIn=self.settings.s3_presign_expires_seconds,
            HttpMethod="PUT",
        )

    def _s3_client(self):
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint_url or None,
            region_name=self.settings.s3_region,
            aws_access_key_id=self.settings.s3_access_key_id,
            aws_secret_access_key=self.settings.s3_secret_access_key,
        )


media_storage = MediaStorage(settings)
