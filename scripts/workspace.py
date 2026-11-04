"""Create private versioned task folders and search the installed car catalog."""
from pathlib import Path
import argparse, json, re
import core as c
from livery import profile

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--profile')
    commands=parser.add_subparsers(dest='command',required=True)
    cars=commands.add_parser('cars');cars.add_argument('query')
    init=commands.add_parser('init');init.add_argument('--name',required=True);init.add_argument('--theme',required=True);init.add_argument('--car-id',required=True,type=int)
    args=parser.parse_args();config=profile(args.profile)
    catalog=c.read(config['carsCatalog'])
    if args.command=='cars':
        words=args.query.casefold().split()
        found=[dict(carId=int(key),**value) for key,value in catalog.items() if all(w in json.dumps(value,ensure_ascii=False).casefold() for w in words)]
        print(json.dumps(found,ensure_ascii=False,indent=2));return
    if str(args.car_id) not in catalog:raise ValueError('Car ID not in the installed catalog; verify exact year/variant')
    if re.search(r'[<>:"/\\|?*\x00-\x1f]',args.name) or args.name.strip(' .')!=args.name:raise ValueError('Use a safe task folder name')
    root=Path(config['backupPolicyRoot']).resolve(strict=True)/args.name
    root.mkdir(exist_ok=False)
    for name in ['sources','concepts','masters','masks','fits','versions','qa','delivery','logs']:(root/name).mkdir()
    c.dump(dict(schema=1,theme=args.theme,carId=args.car_id,car=catalog[str(args.car_id)],
        stage='concepts-and-official-identity-review',references=[],officialAppearanceDefault=True,
        userAdaptations=[],bodyPaint='Choose dominant livery colour unless user specifies; preserve glass/brakes/rims',
        reserves=dict(Left=100,Right=100,Top=100,Back=700,Glass_Left=600,Glass_Right=600),
        smallDecals='Separate groups; user final placement recommended',
        notes='Budgets/reserves are configurable defaults; inspect native geometry before committing design'),root/'brief.json')
    print(json.dumps(dict(task=str(root),brief=str(root/'brief.json'),sharedBackupPolicyRoot=config['backupPolicyRoot']),ensure_ascii=False))

if __name__=='__main__':main()
