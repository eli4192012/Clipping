"""Import extracted title/description pairs into this Mac's private style library."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from posting_style import PROFILE,import_corpus


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus',type=Path,help='UTF-8 JSON: channel and records with integer id, title, description.')
    parser.add_argument('--profile',type=Path,default=PROFILE)
    args=parser.parse_args()
    profile=import_corpus(json.loads(args.corpus.read_text()),args.profile)
    print(f"{profile['channel']}: {profile['total_posts']} posts saved; {len(profile['examples'])} eligible style references.")


if __name__=='__main__':main()
