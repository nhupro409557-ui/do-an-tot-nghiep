import asyncio
import logging
from functools import wraps
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("transaction_retry")

def connection_retry_on_deadlock(max_retries: int = 3, backoff_seconds: float = 0.5):
    """
    Decorator to automatically retry database operations when encountering
    PostgreSQL Deadlock (40P01) or Serialization Failure (40001) errors.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except OperationalError as e:
                    # SQLSTATE codes:
                    # 40001: SERIALIZATION FAILURE
                    # 40P01: DEADLOCK DETECTED
                    sqlstate = getattr(e.orig, "pgcode", None)
                    if sqlstate in ("40001", "40P01") and retries < max_retries:
                        retries += 1
                        sleep_time = backoff_seconds * (2 ** (retries - 1))
                        logger.warning(
                            f"Database conflict detected (SQLSTATE {sqlstate}) in {func.__name__}. "
                            f"Retrying ({retries}/{max_retries}) after {sleep_time:.2f}s..."
                        )
                        # Find the AsyncSession to rollback before retrying
                        session = None
                        # Check self._session (for method calls)
                        if args and hasattr(args[0], "_session") and isinstance(args[0]._session, AsyncSession):
                            session = args[0]._session
                        else:
                            # Search in positional args
                            for arg in args:
                                if isinstance(arg, AsyncSession):
                                    session = arg
                                    break
                            if not session:
                                # Search in keyword args
                                for val in kwargs.values():
                                    if isinstance(val, AsyncSession):
                                        session = val
                                        break
                        if session:
                            await session.rollback()
                        await asyncio.sleep(sleep_time)
                        continue
                    raise e
        return wrapper
    return decorator
