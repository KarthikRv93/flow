"""Ring road example.

Trains a single autonomous vehicle to stabilize the flow of 21 human-driven
vehicles in a variable length ring road.
"""

import json
import os

import ray
import ray.rllib.agents.ppo as ppo
from ray import tune
from ray.rllib.agents.ppo.ppo_policy_graph import PPOPolicyGraph
from ray.tune import run_experiments
from ray.tune.registry import register_env

from flow.utils.registry import make_create_env
from flow.utils.rllib import FlowParamsEncoder
from flow.core.params import SumoParams, EnvParams, InitialConfig, NetParams
from flow.core.vehicles import Vehicles
from flow.controllers import RLController, IDMController, ContinuousRouter

os.environ['MULTIAGENT'] = 'True'

# time horizon of a single rollout
HORIZON = 3000
# number of rollouts per training iteration
N_ROLLOUTS = 2
# number of parallel workers
N_CPUS = 8
# Number of rings
NUM_RINGS = 2

# We place one autonomous vehicle and 22 human-driven vehicles in the network
vehicles = Vehicles()
for i in range(NUM_RINGS):
    vehicles.add(
        veh_id='human_{}'.format(i),
        acceleration_controller=(IDMController, {
            'noise': 0.2
        }),
        routing_controller=(ContinuousRouter, {}),
        num_vehicles=21)
    vehicles.add(
        veh_id='rl_{}'.format(i),
        acceleration_controller=(RLController, {}),
        routing_controller=(ContinuousRouter, {}),
        num_vehicles=1)

flow_params = dict(
    # name of the experiment
    exp_tag='stabilizing_the_ring',

    # name of the flow environment the experiment is running on
    env_name='MultiWaveAttenuationPOEnv',

    # name of the scenario class the experiment is running on
    scenario='MultiLoopScenario',

    # name of the generator used to create/modify network configuration files
    generator='MultiCircleGenerator',

    # sumo-related parameters (see flow.core.params.SumoParams)
    sumo=SumoParams(
        sim_step=0.1,
        render=False,
    ),

    # environment related parameters (see flow.core.params.EnvParams)
    env=EnvParams(
        horizon=HORIZON,
        warmup_steps=750,
        additional_params={
            'max_accel': 1,
            'max_decel': 1,
            'ring_length': [230, 230],
        },
    ),

    # network-related parameters (see flow.core.params.NetParams and the
    # scenario's documentation or ADDITIONAL_NET_PARAMS component)
    net=NetParams(
        additional_params={
            'length': 230,
            'lanes': 1,
            'speed_limit': 30,
            'resolution': 40,
            'num_rings': NUM_RINGS
        }, ),

    # vehicles to be placed in the network at the start of a rollout (see
    # flow.core.vehicles.Vehicles)
    veh=vehicles,

    # parameters specifying the positioning of vehicles upon initialization/
    # reset (see flow.core.params.InitialConfig)
    initial=InitialConfig(bunching = 20.0, spacing='custom'),
)

if __name__ == '__main__':
    ray.init()

    config = ppo.DEFAULT_CONFIG.copy()
    config['num_workers'] = N_CPUS
    config['train_batch_size'] = HORIZON * N_ROLLOUTS
    config['sample_batch_size'] = HORIZON
    config['simple_optimizer'] = True
    config['gamma'] = 0.999  # discount rate
    # config['model'].update({'fcnet_hiddens': [100, 50, 25]})
    # config['use_gae'] = True
    # config['lambda'] = 0.97
    config['lr'] = tune.grid_search([1e-5, 2e-5]) # 1e-5 seems like the right thing
    # config['vf_loss_coeff'] = tune.grid_search([10, 1]) # it seems really important that this is 1 and not 10
    config['vf_clip_param']  = tune.grid_search([1e3, 1e4, 1e5])
    # config['sgd_minibatch_size'] = 128
    # config['kl_target'] = 0.02
    config['num_sgd_iter'] = tune.grid_search([30, 100])
    config['horizon'] = HORIZON
    config['observation_filter'] = 'NoFilter'

    # save the flow params for replay
    flow_json = json.dumps(
        flow_params, cls=FlowParamsEncoder, sort_keys=True, indent=4)
    config['env_config']['flow_params'] = flow_json

    create_env, env_name = make_create_env(params=flow_params, version=0)

    # Register as rllib env
    register_env(env_name, create_env)

    test_env = create_env()
    obs_space = test_env.observation_space
    act_space = test_env.action_space

    def gen_policy():
        return (PPOPolicyGraph, obs_space, act_space, {})

    # Setup PG with an ensemble of `num_policies` different policy graphs
    policy_graphs = {'av': gen_policy()}

    def policy_mapping_fn(_):
        return 'av'

    policy_ids = list(policy_graphs.keys())
    config.update({
        'multiagent': {
            'policy_graphs': policy_graphs,
            'policy_mapping_fn': tune.function(policy_mapping_fn),
            "policies_to_train": ["av"]
        }
    })

    run_experiments({
        flow_params['exp_tag']: {
            'run': 'PPO',
            'env': env_name,
            'checkpoint_freq': 50,
            'stop': {
                'training_iteration': 400
            },
            'config': config,
            'upload_dir': 's3://eugene.experiments/multiagent_tests'
        },
    })
