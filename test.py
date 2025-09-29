from huggingface_hub import HfApi

api = HfApi(endpoint="http://127.0.0.1:48888")

# 建立 repo
# api.create_repo("kohaku/test-model", repo_type="model", private=False)

# 上傳檔案
# api.upload_folder(
#     folder_path="./test_path",
#     path_in_repo="test2/",
#     repo_id="kohaku/test-model",
#     repo_type="model",
# )
# api.upload_file(
#     path_or_fileobj="README.md",
#     path_in_repo="README.md",
#     repo_id="kohaku/test-model",
#     repo_type="model",
# )

# 下載檔案
api.hf_hub_download(
    repo_id="kohaku/test-model", 
    filename="README.md", 
    repo_type="model",
    # local_dir="./test_download"
)
