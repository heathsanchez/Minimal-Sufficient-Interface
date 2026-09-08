"""Matched offline feedback ablation, starting from a pinned witnessed prefix."""
import argparse, json, logging
from pathlib import Path
from arc_agi import Arcade, OperationMode
from agent import observation
from finite_consequence import digest
from parameterized_actions import action_catalog, decode
from multi_level_development import execute_stage
from consequence_search import factors
from closed_feedback import develop


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--evidence',required=True)
    p.add_argument('--game',required=True)
    p.add_argument('--environments-dir',required=True)
    p.add_argument('--max-actions',type=int,default=120)
    p.add_argument('--max-training-actions',type=int,default=10000)
    p.add_argument('--max-episodes',type=int,default=1024)
    p.add_argument('--max-depth',type=int,default=32)
    p.add_argument('--stride',type=int,default=8)
    p.add_argument('--max-grounded-actions',type=int,default=256)
    p.add_argument('--output',default='arc3-closed-feedback.json')
    a=p.parse_args()
    source=json.loads(Path(a.evidence).read_text())
    if source['game']!=a.game or source['status']!='COMPARABLE':
        raise ValueError('Source game or qualification mismatch')
    prior=source['policies'][source['selected_policy']]
    if prior['status']!='COMPARABLE':raise ValueError('Unqualified source policy')
    atom=lambda x:tuple(x) if isinstance(x,list) else x
    prefix=tuple(map(atom,prior['development']['prefix']))
    checkpoint=prior['warm']['final_sha256']
    target=prior['warm']['levels_completed']
    logger=logging.getLogger('arc3-closed-feedback')
    logger.addHandler(logging.NullHandler());logger.setLevel(logging.WARNING)
    def factory():
        arcade=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=a.environments_dir,logger=logger)
        env=arcade.make(a.game)
        if env is None:raise RuntimeError('Environment unavailable')
        class Adapter:
            @property
            def observation_space(self):return env.observation_space
            @property
            def action_space(self):return env.action_space
            def reset(self):return env.reset()
            def step(self,action):
                kind,data=decode(action)
                return env.step(kind,data=data)
            def close(self):return arcade.close_scorecard()
        return Adapter()
    first=factory()
    initial=digest(observation(first.observation_space))
    actions,unsupported=action_catalog(first.action_space,first.observation_space,a.stride,a.max_grounded_actions)
    first.close()
    if initial!=source['initial_sha256'] or not actions:
        raise ValueError('Source initial observation or action interface mismatch')
    source_check=execute_stage(factory(),prefix,(),target,a.max_actions,checkpoint,stop_at_progress=False)
    if (source_check['initial_sha256']!=initial or source_check['checkpoint_sha256']!=checkpoint
            or source_check['levels_completed']!=target or source_check['state']!=prior['warm']['state']
            or source_check['status'] not in ('OBSERVED','PREFIX_TERMINATED')):
        raise ValueError('Witnessed source prefix did not replay')
    options=tuple(tuple(map(atom,o)) for o in prior['development']['options'])
    seeds=tuple(dict.fromkeys(options+tuple(f for o in options for f in factors(o,a.max_depth))))
    arms={}
    for name,feedback in (('ablation',False),('feedback',True)):
        learned=develop(factory,actions,prefix,checkpoint,a.max_actions,
                        a.max_training_actions,a.max_episodes,a.max_depth,
                        seed_programs=seeds,feedback=feedback)
        best=tuple(learned['development']['best_prefix'])
        if learned['status']=='VERIFIED_WIN':best=tuple(learned['result']['executed'])
        deployment=execute_stage(factory(),(),best,0,a.max_actions,stop_at_progress=False)
        matched=deployment['initial_sha256']==initial
        arms[name]={'development':learned,'deployment':deployment,
                    'matched_initial':matched,'verified_win':bool(matched and deployment['state']=='WIN')}
    def quality(arm):
        d=arm['deployment']
        return (int(arm['verified_win']),d['levels_completed'],-d['actions'])
    comparable=all(x['matched_initial'] for x in arms.values())
    improved=comparable and quality(arms['feedback'])>quality(arms['ablation'])
    result={'status':'COMPARABLE' if comparable else 'INCONCLUSIVE_UNMATCHED_START',
            'game':a.game,'mode':'offline','competition_submission':False,'model_calls':0,
            'source_run':34192005884,'source_evidence_sha256':digest(source),
            'initial_sha256':initial,'source_checkpoint':checkpoint,'source_prefix':prefix,
            'source_replay':source_check,'grounded_actions':len(actions),'unsupported_action_ids':unsupported,
            'bounds':{'budget':a.max_actions,'max_training_actions':a.max_training_actions,
                      'max_episodes':a.max_episodes,'max_depth':a.max_depth,'stride':a.stride},
            'arms':arms,'improved':bool(improved)}
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True,default=str)+'\n')
    print('ARC3_CLOSED_FEEDBACK='+json.dumps({
        'status':result['status'],'improved':result['improved'],
        'arms':{name:{'status':arm['development']['status'],
                      'training_actions':arm['development']['training_actions'],
                      'training_episodes':arm['development']['training_episodes'],
                      'transitions':arm['development']['development']['transitions'],
                      'installed_options':arm['development']['development']['options'],
                      'actions':arm['deployment']['actions'],'levels_completed':arm['deployment']['levels_completed'],
                      'state':arm['deployment']['state'],'score':arm['deployment']['score'],
                      'verified_win':arm['verified_win']} for name,arm in arms.items()}},sort_keys=True))

if __name__=='__main__':main()
