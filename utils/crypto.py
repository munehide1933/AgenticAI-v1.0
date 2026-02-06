import base64
from pathlib import Path

from cryptography.fernet import Fernet


class ContentEncryptor:
    """内容加密器 - 用于加密敏感会话数据"""

    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)

    def _get_or_create_key(self) -> bytes:
        """获取或创建加密密钥"""
        key_file = Path(__file__).parent.parent / "config" / ".encryption_key"

        if key_file.exists():
            with open(key_file, "rb") as f:
                return f.read()
        else:
            # 生成新密钥
            key = Fernet.generate_key()

            # 保存密钥（生产环境应使用密钥管理服务）
            key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(key_file, "wb") as f:
                f.write(key)

            print(f"⚠️ 已生成新的加密密钥: {key_file}")
            print("⚠️ 请妥善保管此密钥文件！")

            return key

    def encrypt(self, text: str) -> str:
        """加密文本"""
        if not text:
            return ""
        try:
            encrypted = self.cipher.encrypt(text.encode("utf-8"))
            return base64.b64encode(encrypted).decode("utf-8")
        except Exception as e:
            print(f"加密失败: {e}")
            return text

    def decrypt(self, encrypted_text: str) -> str:
        """解密文本"""
        if not encrypted_text:
            return ""
        try:
            encrypted = base64.b64decode(encrypted_text.encode("utf-8"))
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode("utf-8")
        except Exception:
            # 如果解密失败，可能是明文数据（向后兼容）
            return encrypted_text


# 全局加密器实例
encryptor = ContentEncryptor()
