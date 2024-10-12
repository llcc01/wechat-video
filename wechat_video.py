import asyncio

from mitmproxy.tools import dump
from mitmproxy import http,options
import re
import os
import pathlib
import shutil
import threading
import wget
from datetime import datetime
from tqdm import tqdm
import logging

CACHE_PATH = os.path.join(pathlib.Path.home(), ".xwechat/radium/web/profiles")

DOWNLOAD_PATH = os.path.join(pathlib.Path.home(), "Downloads/wechat_video")

try:
    shutil.rmtree(CACHE_PATH)
except FileNotFoundError:
    logging.info(f"{CACHE_PATH} not found")
logging.info(f"removed {CACHE_PATH}")

last_url = None

last_key = None


def download_thread(url: str, key: bytes):
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d-%H-%M-%S")
    file_path = os.path.join(DOWNLOAD_PATH, dt_string + ".mp4")
    print(f"Downloading {url} to {file_path}")
    wget.download(url, out=file_path)
    print()
    with open(file_path, "rb+") as f:
        f.seek(0)
        encrypted = f.read(len(key))
        decrypted = b''
        for i in tqdm(range(len(encrypted)), desc="Decrypting"):
            decrypted += bytes([encrypted[i] ^ key[i]])
        f.seek(0)
        f.write(decrypted)
            


class InterceptRequest(object):

    def __init__(self):
        pass
 
    def __del__(self):
        pass

    def response(self, flow: http.HTTPFlow):
        global last_url
        global last_key
        # ctx.log.info(flow.request.pretty_url)
        if flow.request.pretty_url.endswith("/worker_release.js"):
            pattern = r"([a-zA-Z]*)\.decryptor_array\.set\(([a-zA-Z]*)\.reverse\(\)\)"
            repl = r"var rr=\2.reverse();fetch('https://example.com/post',{method:'POST',headers:{'Content-Type':'application/octet-stream',},body:rr,}).then(response=>{console.log(response.ok,response.body)});\1.decryptor_array.set(rr);"
            new_js = re.sub(pattern, repl, flow.response.text)
            flow.response.set_text(new_js)
        elif flow.request.pretty_url.startswith(
            "https://finder.video.qq.com/251/20302/stodownload"
        ):
            # print(flow.request.pretty_url)
            last_url = flow.request.pretty_url


    def request(self, flow: http.HTTPFlow):
        global last_key
        if flow.request.pretty_url == "https://example.com/post":
            if flow.request.method == "POST":
                rr = flow.request.get_content()
                last_key = rr
                if last_url is not None:
                    threading.Thread(
                        target=download_thread, args=(last_url, last_key)
                    ).start()

            flow.response = http.Response.make(
                200,
                b"OK",
                {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST,GET,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
            )



async def start_proxy(host, port):
    # opts = main.options.Options(listen_host=host, listen_port=port)
    opts = options.Options(listen_host=host, listen_port=port)
 
    master = dump.DumpMaster(
        opts,
        with_termlog=False,
        with_dumper=False,
    )
    master.addons.add(InterceptRequest())
 
    await master.run()
    return master
 
 
def func_main():
    asyncio.run(start_proxy('127.0.0.1', 8080))
 
 
if __name__ == '__main__':
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    func_main()
