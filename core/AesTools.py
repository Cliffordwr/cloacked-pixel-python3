import hashlib
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

'''
Thanks to
http://stackoverflow.com/questions/12524994/encrypt-decrypt-using-pycrypto-aes-256
'''
class AESCipher:

    def __init__(self, key): 
        self.bs = 32	# Block size
        self.key = hashlib.sha256(key).digest()	# 32 bit digest

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv, use_aesni=True) # 启用AES-NI指令集的硬件加速
        return iv + cipher.encrypt(raw)

    def decrypt(self, enc):
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv, use_aesni=True) # 启用AES-NI指令集的硬件加速
        return self._unpad(cipher.decrypt(enc[AES.block_size:]))

    def _pad(self, s):
        padding = self.bs - len(s) % self.bs
        return s + padding * bytes([padding])
    
    def check_message_size(self, out_data, encrypted_data):
        if out_data is None:
            return False
        return (len(out_data) + 32 - len(out_data) % 32) == len(encrypted_data) - 16

    def _unpad(self, s):
        try:
            return unpad(s, self.bs, style='pkcs7')
        except Exception:
            return None
