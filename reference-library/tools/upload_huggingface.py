from pathlib import Path
from huggingface_hub import HfApi
root=Path(__file__).resolve().parent.parent
api=HfApi()
assert api.whoami()['name']=='bensblueprints','Wrong Hugging Face account'
api.create_repo('bensblueprints/consistent-pet',repo_type='dataset',private=False,exist_ok=True)
api.upload_large_folder(repo_id='bensblueprints/consistent-pet',repo_type='dataset',folder_path=root,num_workers=6,
 allow_patterns=['references/**','previews/**','print-variants/**','tools/*.py','README.md','catalog.json','catalog.csv','metadata.jsonl','inventory.json','index.html','gallery-data.js'],print_report_every=30)
print('Hugging Face upload finished')
