import os

os.environ["HF_ENDPOINT"] = "http://127.0.0.1:28080"
from huggingface_hub import HfApi

api = HfApi(endpoint="http://127.0.0.1:28080")

# 建立 repo
try:
    api.create_repo("KBlueLeaf/test-2", repo_type="model", private=False)
except Exception as e:
    print(e)

os.makedirs("./test_path", exist_ok=True)
# 上傳檔案
with open("./test_path/large", "wb") as f:
    f.write(os.urandom(1024 * 1024 * 20))
with open("./test_path/1", "wb") as f:
    f.write(os.urandom(1024))

api.upload_folder(
    folder_path="./test_path",
    path_in_repo="test2/",
    repo_id="KBlueLeaf/test-2",
    repo_type="model",
)
api.upload_file(
    path_or_fileobj="README.md",
    path_in_repo="README.md",
    repo_id="KBlueLeaf/test-2",
    repo_type="model",
)
api.get_paths_info

# 下載檔案
file = api.hf_hub_download(
    repo_id="KBlueLeaf/test-2",
    filename="README.md",
    repo_type="model",
)
with open(file, "rb") as f:
    print(f.read()[:50])

file = api.hf_hub_download(
    repo_id="KBlueLeaf/test-2", repo_type="model", filename="test2/1"
)
with open(file, "rb") as f:
    print(f.read()[:50])


file = api.hf_hub_download(
    repo_id="KBlueLeaf/test-2", repo_type="model", filename="test2/large"
)
with open(file, "rb") as f:
    print(f.read()[:50])

# 刪除檔案
api.delete_file(
    path_in_repo="test2/1",
    repo_id="KBlueLeaf/test-2",
    repo_type="model",
)

# 刪除 repo
# api.delete_repo(repo_id="KBlueLeaf/test-2", repo_type="model")
