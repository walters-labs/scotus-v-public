"""Package reviewed topic labels with otherwise unchanged survey search assets."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

from scvpublic.build import digest
from scvpublic.encoding import Encoder
from scvpublic.survey_search import SurveySearch
from scvpublic.survey_topics import TopicSearch


def build(artifact, bundle, descriptions, output):
    if output.exists():
        raise FileExistsError(output)
    baseline = SurveySearch(bundle, artifact, Encoder(bundle))
    if baseline.topic_router:
        raise ValueError('Use a baseline without topic routing')
    router = TopicSearch(baseline, descriptions)
    spec = json.loads(descriptions.read_text())
    metadata = dict(version=1, status=spec['status'], scope=spec['scope'],
        source_sha256=digest(descriptions), entries=[{k:entry[k] for k in
            ('source','code','topic','source_text_sha256')} for entry in spec['entries']])
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        target = Path(temp)/'bundle'
        shutil.copytree(bundle, target)
        name = 'survey-topic-metadata.json'
        (target/name).write_text(json.dumps(metadata,indent=2)+'\n')
        manifest = json.loads((target/'manifest.json').read_text())
        manifest['survey_topic_routing'] = 'reviewed-phrases-v1'
        manifest['survey_topic_questions'] = len(router.entries)
        manifest['files'][name] = digest(target/name)
        (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        SurveySearch(target,artifact,baseline.encoder)
        target.rename(output)
    print(json.dumps(dict(reviewed_questions=len(router.entries),output=str(output))))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('artifact','bundle','descriptions','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    build(args.artifact,args.bundle,args.descriptions,args.output)
