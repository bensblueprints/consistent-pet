"""Mirror committed, public workflow/source files to the existing HF dataset."""
from pathlib import Path
import subprocess,tempfile,tarfile,io

def mirror(repo,dataset):
    from huggingface_hub import HfApi
    if dataset!='bensblueprints/consistent-pet':raise ValueError('Unexpected mirror destination')
    tracked=subprocess.check_output(['git','ls-files'],cwd=repo,text=True).splitlines()
    allowed=[p for p in tracked if p.startswith('workflows/') or p.startswith('scripts/') and p.endswith(('.py','.js','.html')) or p in ('HANDOFF.md','AGENTS.md','docs/WORKFLOW.md','docs/RECOVERY.md')]
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    with tempfile.TemporaryDirectory(prefix='pet-public-mirror-') as tmp:
        root=Path(tmp)
        archive=subprocess.check_output(['git','archive',revision,'workflows','scripts','HANDOFF.md','AGENTS.md','docs'],cwd=repo)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for member in tar:
                if member.isfile() and member.name in allowed:
                    target=root/member.name;target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(tar.extractfile(member).read())
        result=HfApi().upload_folder(repo_id=dataset,repo_type='dataset',folder_path=root,commit_message='Mirror saved portrait workflows and recovery source '+revision[:8])
    return str(result.oid)
