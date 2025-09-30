import os

os.environ["HF_ENDPOINT"] = "http://127.0.0.1:48888"
from huggingface_hub import HfApi

api = HfApi(endpoint="http://127.0.0.1:48888")

# 建立 repo
try:
    api.create_repo("kohaku/test-2", repo_type="model", private=False)
except Exception as e:
    print(e)

# 上傳檔案
with open("./test_path/large", "wb") as f:
    f.write(os.urandom(1024 * 1024 * 20))
with open("./test_path/1", "wb") as f:
    f.write(os.urandom(1024))

api.upload_folder(
    folder_path="./test_path",
    path_in_repo="test2/",
    repo_id="kohaku/test-2",
    repo_type="model",
)
api.upload_file(
    path_or_fileobj="README.md",
    path_in_repo="README.md",
    repo_id="kohaku/test-2",
    repo_type="model",
)

# 下載檔案
file = api.hf_hub_download(
    repo_id="kohaku/test-2",
    filename="README.md",
    repo_type="model",
)
with open(file, "r") as f:
    print(f.read()[:50])

file = api.hf_hub_download(
    repo_id="kohaku/test-2", repo_type="model", filename="test2/1"
)
with open(file, "rb") as f:
    print(f.read()[:50])
