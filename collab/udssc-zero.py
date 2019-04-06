"""Example of modified minicity network with human-driven vehicles."""
from flow.controllers import SumoCarFollowingController
from flow.controllers import SumoLaneChangeController
from flow.core.experiment import SumoExperiment
from flow.core.params import SumoParams, EnvParams, NetParams, InitialConfig
from flow.core.vehicles import Vehicles
from flow.envs.loop.loop_accel import AccelEnv, ADDITIONAL_ENV_PARAMS
from flow.envs.minicity_env import MinicityEnv
from flow.scenarios.minicity import MinicityScenario, ADDITIONAL_NET_PARAMS
from flow.controllers.routing_controllers import MinicityRouter, MinicityMatrixRouter
import numpy as np

np.random.seed(204)


def minicity_example(render=None,
                     save_render=None,
                     sight_radius=None,
                     pxpm=None,
                     show_radius=None):
    """
    Perform a simulation of vehicles on modified minicity of University of
    Delaware.

    Parameters
    ----------
    render: bool, optional
        specifies whether to use sumo's gui during execution

    Returns
    -------
    exp: flow.core.SumoExperiment type
        A non-rl experiment demonstrating the performance of human-driven
        vehicles on the minicity scenario.
    """
    sumo_params = SumoParams(render=False)

    if render is not None:
        sumo_params.render = render

    if save_render is not None:
        sumo_params.save_render = save_render

    if sight_radius is not None:
        sumo_params.sight_radius = sight_radius

    if pxpm is not None:
        sumo_params.pxpm = pxpm

    if show_radius is not None:
        sumo_params.show_radius = show_radius

    vehicles = Vehicles()
    vehicles.add(
        veh_id="manned",
        speed_mode=0b11111,
        lane_change_mode=0b011001010101,
        acceleration_controller=(SumoCarFollowingController, {}),
        lane_change_controller=(SumoLaneChangeController, {}),
        routing_controller=(MinicityMatrixRouter, {}),
        initial_speed=0,
        num_vehicles=50)

    env_params = EnvParams(additional_params=ADDITIONAL_ENV_PARAMS)

    additional_net_params = ADDITIONAL_NET_PARAMS.copy()
    net_params = NetParams(
        no_internal_links=False, additional_params=additional_net_params)

    initial_config = InitialConfig(
        spacing="random",
        min_gap=2.5
    )
    scenario = MinicityScenario(
        name="minicity",
        vehicles=vehicles,
        initial_config=initial_config,
        net_params=net_params
    )

    env = MinicityEnv(env_params, sumo_params, scenario)

    return SumoExperiment(env, scenario)


if __name__ == "__main__":
    exp = minicity_example(render=True,
                           save_render=False,
                           sight_radius=50,
                           pxpm=3,
                           show_radius=False)
    exp.run(1, 10000)