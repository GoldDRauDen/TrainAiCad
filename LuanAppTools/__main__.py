"""python -m LuanAppTools --data-dir <local state> --repo-root <checkout>."""
import argparse
import os
from pathlib import Path
import uvicorn
from LuanAppTools.service.api import create_app


def main(argv=None):
    parser=argparse.ArgumentParser(description='LuanAppTools local CAD review dashboard')
    default=Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local'/'share'))/'LuanAppTools'
    parser.add_argument('--data-dir',type=Path,default=default)
    parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args(argv)
    if not 1<=args.port<=65535: parser.error('port must be 1–65535')
    uvicorn.run(create_app(args.data_dir,args.repo_root),host='127.0.0.1',port=args.port,workers=1)


if __name__=='__main__':
    main()
