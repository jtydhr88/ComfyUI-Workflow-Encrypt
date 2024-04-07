import configparser
import mimetypes
import shutil
import traceback

import folder_paths
import os
import sys
import threading
import locale
import subprocess  # don't remove this
from tqdm.auto import tqdm
import concurrent
from urllib.parse import urlparse
import http.client
import re
import nodes
import hashlib
from datetime import datetime
from cryptography.fernet import Fernet
import json

comfy_path = os.path.dirname(folder_paths.__file__)
js_path = os.path.join(comfy_path, "web", "extensions")

comfyui_workflow_encrypt_path = os.path.dirname(__file__)

def setup_js():
    js_dest_path = os.path.join(js_path, "comfyui-workflow-encrypt")

    # setup js
    if not os.path.exists(js_dest_path):
        os.makedirs(js_dest_path)
    js_src_path = os.path.join(comfyui_workflow_encrypt_path, "js", "comfyui-workflow-encrypt.js")

    print(f"### ComfyUI-Workflow-Encrypt: Copy .js from '{js_src_path}' to '{js_dest_path}'")
    shutil.copy(js_src_path, js_dest_path)


setup_js()

import server
from aiohttp import web

def handle_stream(stream, prefix):
    stream.reconfigure(encoding=locale.getpreferredencoding(), errors='replace')
    for msg in stream:
        if prefix == '[!]' and ('it/s]' in msg or 's/it]' in msg) and ('%|' in msg or 'it [' in msg):
            if msg.startswith('100%'):
                print('\r' + msg, end="", file=sys.stderr),
            else:
                print('\r' + msg[:-1], end="", file=sys.stderr),
        else:
            if prefix == '[!]':
                print(prefix, msg, end="", file=sys.stderr)
            else:
                print(prefix, msg, end="")

def run_script(cmd, cwd='.'):
    if len(cmd) > 0 and cmd[0].startswith("#"):
        print(f"[ComfyUI-Workflow-Encrypt] Unexpected behavior: `{cmd}`")
        return 0

    process = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

    stdout_thread = threading.Thread(target=handle_stream, args=(process.stdout, ""))
    stderr_thread = threading.Thread(target=handle_stream, args=(process.stderr, "[!]"))

    stdout_thread.start()
    stderr_thread.start()

    stdout_thread.join()
    stderr_thread.join()

    return process.wait()

try:
    from nodes import NODE_CLASS_MAPPINGS
except:
    requirements_path = os.path.join(comfyui_workflow_encrypt_path, "requirements.txt")

    print(f"## ComfyUI-Workflow-Encrypt: installing dependencies")

    run_script([sys.executable, '-s', '-m', 'pip', 'install', '-r', requirements_path])

    try:
        from nodes import NODE_CLASS_MAPPINGS
    except:
        print(f"## [ERROR] ComfyUI-Workflow-Encrypt: Attempting to reinstall dependencies using an alternative method.")
        run_script([sys.executable, '-s', '-m', 'pip', 'install', '--user', '-r', requirements_path])

        try:
            from .nodes import NODE_CLASS_MAPPINGS
        except:
            print(f"## [ERROR] ComfyUI-Workflow-Encrypt: Failed to install package in the correct Python environment.")
            traceback.print_exc()

    print(f"## ComfyUI-Workflow-Encrypt: installing dependencies done.")

@server.PromptServer.instance.routes.post("/workflow_encrypt/save_encrypt_method")
async def save_encrypt_method(request):
    json_data = await request.json()

    current_workflow = json_data['workflow']
    workflow_str = json.dumps(current_workflow)

    key = Fernet.generate_key()
    cipher_suite = Fernet(key)

    key_output = key.decode('utf-8')

    print("Please store the key carefully; it will only be shown here once:")
    print(key_output)
    print("")

    encrypted_data = cipher_suite.encrypt(workflow_str.encode('utf-8'))

    json_obj = {
        'key': key_output,
        'encrypted_data': encrypted_data.decode('utf-8')
    }

    return web.json_response(json_obj, content_type='application/json')

@server.PromptServer.instance.routes.post("/workflow_encrypt/load_decrypted_method")
async def load_decrypted_method(request):
    json_data = await request.json()

    try:
        key_bytes = json_data['decryptedKey'].encode()
        encrypted_content = json_data['fileContent'].encode()

        cipher_suite = Fernet(key_bytes)

        decrypted_data = cipher_suite.decrypt(encrypted_content)

        decrypted_json = json.loads(decrypted_data.decode('utf-8'))

        print("Decrypted success")

        return web.json_response(decrypted_json, content_type='application/json')
    except Exception as e:
        print("Decrypted failed")

        json_obj = {
            'status': 'Decrypted failed'
        }

        return web.json_response(json_obj, content_type='application/json')

__all__ = ['NODE_CLASS_MAPPINGS']