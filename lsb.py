import os
import sys
import struct
import itertools
import numpy as np
from PIL import Image
from core import PathCore
from core.errorCore import *
from bitarray import bitarray
import matplotlib.pyplot as plt
from core.AesTools import AESCipher


# Decompose a binary file into an array of bits
def decompose(data):
    v = bitarray()

    # Pack file len in 4 bytes
    fSize = len(data)
    bytes_data = struct.pack("i", fSize)
    v.frombytes(bytes_data)
    v.frombytes(data)
    return v.tolist()

# Assemble an array of bits into a binary file
def assemble(v):
    bits = bitarray(v)
    bytes_data = bits.tobytes()
    payload_size = int.from_bytes(bytes_data[:4], byteorder="little", signed=False)
    return payload_size, bytes_data[4: payload_size + 4]

def set_bit(byte, bit, value):
    """
    将一个字节的第 bit 位改为 value，其中 value 只能是 0 或 1。
    """
    if value == 0:
        # 将第 bit 位改为 0
        return byte & ~(1 << bit)
    elif value == 1:
        # 将第 bit 位改为 1
        return byte | (1 << bit)
    else:
        # value 只能是 0 或 1，否则抛出异常
        raise ValueError("value must be 0 or 1")

# Embed payload file into LSB bits of an image
def embed(imgPath, payload, password):
    # Process source image
    img = Image.open(imgPath)
    (width, height) = img.size
    conv = img.convert("RGBA").getdata()
    print("[*] Input image size: %dx%d pixels." % (width, height))
    max_size = width*height*3.0/8/1024		# max payload size
    print("[*] Usable payload size: %.2f KB." % (max_size))

    with open(payload, "rb") as f:
        data = f.read()
    print("[+] Payload size: %.3f KB " % (len(data)/1024.0))

    # Encypt
    cipher = AESCipher(password.encode())
    data_enc = cipher.encrypt(data)

    # Process data from payload file
    v = decompose(data_enc)

    # Add until multiple of 3
    while(len(v)%3):
        v.append(0)

    payload_size = len(v)/8/1024.0
    print("[+] Encrypted payload size: %.3f KB " % (payload_size))
    if (payload_size > max_size - 4):
        print("[-] Cannot embed. File too large")
        sys.exit()

    # Create output image
    steg_img = Image.new('RGBA',(width, height))
    data_img = steg_img.getdata()

    idx = 0

    for h in range(height):
        for w in range(width):
            (r, g, b, a) = conv.getpixel((w, h))
            if idx < len(v):
                r = set_bit(r, 0, v[idx])
                g = set_bit(g, 0, v[idx+1])
                b = set_bit(b, 0, v[idx+2])
            data_img.putpixel((w,h), (r, g, b, a))
            idx = idx + 3

    filePrefix, _, _ = PathCore.get_save_info(imgPath)
    steg_img.save(f"{filePrefix}-stego.png", "PNG")

    print(f"[+] {payload} embedded successfully!")

def get_LSBs(in_file):
    _, fileName, _ = PathCore.get_save_info(in_file)
    saveDir = os.path.dirname(in_file)
    savePath = os.path.join(saveDir, f"{fileName}.out")

    # Read Img
    img = np.array(Image.open(in_file).convert("RGB"))
    row, col = img.shape[:2]

    # Extract LSBs
    img = img & 1
    img = np.ravel(img).tolist() # 行优先
    payload_size, encrypted_data = assemble(img)
    # 返回的encrypted_data存在前16字节位IV，所以要删掉16字节
    
    if (payload_size - 16) % 32 != 0:
        raise CustomeError("[-] 图像负载的AES信息大小不为32的倍数, 所以不存在该隐写!")
    if payload_size > os.path.getsize(in_file):
        raise CustomeError("[-] 图像大小小于图像负载的AES信息大小, 所以不存在该隐写!")
    return row, col, fileName, savePath, payload_size, encrypted_data

def check_message_size(out_data, encrypted_data):
    return (len(out_data) + 32 - len(out_data) % 32) == len(encrypted_data) - 16

@handle_exceptions
def extract(in_file, password):
    '''
    Extract data embedded into LSB of the input file
    '''
    row, col, fileName, savePath, payload_size, encrypted_data = get_LSBs(in_file)
    print(f"[+] Image size: {col}x{row} pixels, Payload size(AES): {payload_size / 1024:.3f} KB, key: {password}")

    # Decrypt
    aes = AESCipher(password.encode())
    out_data = aes.decrypt(encrypted_data)
    if not aes.check_message_size(out_data, encrypted_data):
        raise CustomeError("[-] 字节大小不正确, 所以密码不正确!")
    
    with open(savePath, "wb") as out_f:
        out_f.write(out_data)
    print(f"[+] Written extracted data to {fileName}.out.")

# Statistical analysis of an image to detect LSB steganography
def analyse(in_file):
    '''
    - Split the image into blocks.
    - Compute the average value of the LSBs for each block.
    - The plot of the averages should be around 0.5 for zones that contain
      hidden encrypted messages (random data).
    '''
    BS = 100	# Block size 
    img = Image.open(in_file)
    (width, height) = img.size
    print("[+] Image size: %dx%d pixels." % (width, height))
    conv = img.convert("RGBA").getdata()

    # Extract LSBs
    vr = []	# Red LSBs
    vg = []	# Green LSBs
    vb = []	# LSBs
    for h, w in itertools.product(range(height), range(width)):
        (r, g, b, a) = conv.getpixel((w, h))
        vr.append(r & 1)
        vg.append(g & 1)
        vb.append(b & 1)

    # Average colours' LSB per each block
    avgR = []
    avgG = []
    avgB = []
    for i in range(0, len(vr), BS):
        avgR.append(np.mean(vr[i:i + BS]))
        avgG.append(np.mean(vg[i:i + BS]))
        avgB.append(np.mean(vb[i:i + BS]))

    # Nice plot 
    numBlocks = len(avgR)
    blocks = list(range(numBlocks))
    plt.axis([0, len(avgR), 0, 1])
    plt.ylabel('Average LSB per block')
    plt.xlabel('Block number')

#	plt.plot(blocks, avgR, 'r.')
#	plt.plot(blocks, avgG, 'g')
    plt.plot(blocks, avgB, 'bo')

    plt.show()

def usage(progName):
    print("LSB steganogprahy. Hide files within least significant bits of images.\n")
    print("Usage:")
    print(f"  {progName} hide <img_file> <payload_file> <password>")
    print(f"  {progName} extract <stego_file> <password>")
    print(f"  {progName} analyse <stego_file>")
    sys.exit()

@handle_exceptions
def check_img_exists(imgPath):
    if not os.path.exists(imgPath):
        raise CustomeError("[-] 图片不存在, 请您检查一下你传入的图片是否存在!")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        usage(sys.argv[0])
        
    imgPath = os.path.abspath(sys.argv[2])
    error, output = check_img_exists(imgPath)
    if error:
        print(output)
        exit(-1)
    
    if sys.argv[1] == "hide":
        pyloadPath = os.path.abspath(sys.argv[3])
        password = sys.argv[4]
        embed(imgPath, pyloadPath, password)
    elif sys.argv[1] == "extract":
        password = sys.argv[3]
        error, output = extract(imgPath, password)
        if error:
            print(output)
    elif sys.argv[1] == "analyse":
        analyse(imgPath)
    else:
        print("[-] Invalid operation specified")
        
