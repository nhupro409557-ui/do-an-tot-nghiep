export function getAuthErrorMessage(code?: string, fallback = 'Có lỗi xảy ra. Vui lòng thử lại.') {
  switch (code) {
    case 'auth/invalid-credential':
    case 'auth/wrong-password':
    case 'auth/user-not-found':
      return 'Email hoặc mật khẩu không đúng.';
    case 'http/409':
    case 'auth/email-already-in-use':
      return 'Email này đã được đăng ký.';
    case 'auth/weak-password':
      return 'Mật khẩu cần có ít nhất 6 ký tự.';
    case 'http/400':
      return fallback;
    case 'auth/requires-recent-login':
      return 'Vui lòng đăng nhập lại trước khi thực hiện thao tác này.';
    case 'auth/too-many-requests':
      return 'Bạn thao tác quá nhiều lần. Vui lòng thử lại sau.';
    case 'auth/invalid-reset-token':
      return 'Liên kết đặt lại mật khẩu đã hết hạn.';
    case 'auth/invalid-reset-code':
      return 'Mã xác nhận không hợp lệ hoặc đã hết hạn.';
    default:
      return fallback;
  }
}
