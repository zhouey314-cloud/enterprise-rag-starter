"""Write a licensed fictional local demo; deliberately refuses existing output files."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from local_fixtures import load_corpus, materialize

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',default='.rag-data/demo')
args=parser.parse_args()
documents=[d for d in load_corpus()['documents'] if d['metadata']['doc_id'] in {'support-hours','travel-finance-pages','people-handbook'}]
manifest=materialize(args.out,documents)
print(json.dumps({'status':'CREATED','manifest':str(Path(args.out)/'manifest.json'),'documents':len(manifest),'provenance':'synthetic_unverified','license':'MIT'}))
