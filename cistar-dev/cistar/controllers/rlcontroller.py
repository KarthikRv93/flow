
from cistar.controllers.base_controller import BaseController


class RLController(BaseController):
    """Base Rl Controller (assumes acceleration by Default)
    """

    def __init__(self, veh_id, deacc_max=3, tau=0, dt=0.1):
        """Instantiates a CFM controller

        Arguments:
            veh_id -- Vehicle ID for SUMO identification

        Keyword Arguments:
            acc_max {number} -- [max acceleration] (default: {15})
            tau {number} -- [time delay] (default: {0})
            dt {number} -- [timestep] (default: {0.1})
        """

        controller_params = {"delay": tau/dt, "max_deaccel": deacc_max}
        BaseController.__init__(self, veh_id, controller_params)



class RLVelocityController(RLController):

    """
    Rl Controller that assumes velocity
    """
    def get_safe_action(self, env, action):
        v_safe = self.safe_velocity(env)
        if v_safe < action:
            print(v_safe, action)
        return min(action, v_safe)