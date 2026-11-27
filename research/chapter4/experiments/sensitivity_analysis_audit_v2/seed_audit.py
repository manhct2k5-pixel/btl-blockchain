"""Verify the actual contract passed to generation, not the printed sensitivity seed."""
from audit_common import *
from main_generator import generate_world
def generator_contract():
    return read(MAIN/'MC_MAIN_CONTRACT.json')
def seed_probe(generator=None):
    generator=generator or generate_world
    c=generator_contract()
    return generator(c,'MAIN',0)
def main():
    c=generator_contract();registered=read(ORIGINAL/'SENSITIVITY_EXPERIMENT_CONTRACT.json')
    worlds=read(MAIN/'WORLDS.json');mismatches=[]
    rows=[]
    for w in worlds:
        generated=generate_world(c,w['group'],w['replicate_id'])
        matches=generated['config']==w['config'] and generated['master_seed']==w['master_seed']
        if not matches:mismatches.append(w['world_id'])
        rows.append(dict(world_id=w['world_id'],actual_master_seed=c['master_seed'],
            stored_master_seed=w['master_seed'],generated_config_hash=digest(generated['config']),
            stored_config_hash=digest(w['config']),matches=matches))
    dump(ROOT/'WORLD_SEED_REGENERATION.json',rows)
    result=dict(registered_sensitivity_master_seed=registered['master_seed'],
        printed_sensitivity_master_seed=4302028,actually_passed_master_seed=c['master_seed'],
        registered_seed_was_assigned_to_generator=False,
        regenerated_worlds=len(worlds),matching_worlds=len(worlds)-len(mismatches),mismatches=mismatches,
        reason='run_sensitivity loads main contract and changes sizes, never c[master_seed]',
        no_new_independent_sensitivity_worlds=True,source_main_contract_sha256=sha(MAIN/'MC_MAIN_CONTRACT.json'))
    dump(ROOT/'MASTER_SEED_AUDIT.json',result)
    if mismatches:raise AssertionError('Source world regeneration mismatch')
    print(result)
    return result
if __name__=='__main__':main()
