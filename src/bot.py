from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.structures.ball_prediction_struct import BallPrediction, Slice

import math
import Sequences
from States import State
from util.Localizator import getBigBoostPadIndices

from util.orientation import Orientation
from util.ball_prediction_analysis import find_matching_slice, find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target, relativeDirection
from util.sequence import Sequence, ControlStep
from util.vec import Vec3


class MyBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()

    def initialize_agent(self):
        # Set up information about the boost pads now that the game is active and the info is available
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        """
        This function will be called by the framework many times per second. This is where you can
        see the motion of the ball, etc. and return controls to drive your car.
        """

        # Keep our boost pad info updated with which pads are currently active
        self.boost_pad_tracker.update_boost_status(packet)

        # This is good to keep at the beginning of get_output. It will allow you to continue
        # any sequences that you may have started during a previous call to get_output.
        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls

        # Gather some information about our car and the ball
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)
        ball_velocity = Vec3(packet.game_ball.physics.velocity)
        car_rotation = Orientation(my_car.physics.rotation)
        gameTime = packet.game_info.seconds_elapsed
        target_location = ball_location

        target_location, t = self.calculatePrediction(car_location, ball_location, ball_velocity, gameTime)

        currentState = State(my_car, ball_location, ball_velocity, target_location, t, self.renderer)

        # Draw some things to help understand what the bot is thinking
        debugText = 'forward ={}\n'.format(car_rotation.forward)
        debugText += 'pitch ={}\n'.format(car_rotation.pitch)
        debugText += 'right ={}\n'.format(car_rotation.right)
        debugText += 'roll ={}\n'.format(car_rotation.roll)
        debugText += 'up ={}\n'.format(car_rotation.up)
        debugText += 'yaw ={}\n'.format(car_rotation.yaw)
        debugText += 'time to target: actual={}, expected={}\n'.format(round(currentState.timeToTargetAtCurrentSpeed(), 2), round(currentState.timeToTarget, 2))
        debugText += 'debug ={}\n'.format(ball_location)
        
        #debugText += '{}\n'.format()
       

        controls = SimpleControllerState()


        target_location = Sequences.goalie(currentState, target_location)
        target_location = Sequences.boostManagement(currentState, packet.game_boosts, target_location)
        target_location = Sequences.striker(currentState, target_location)

        currentState.target = target_location

        if currentState.flipToGetSpeed():
            return self.begin_front_flip(packet)
        controls = Sequences.catReflexes(currentState, controls)
        controls = Sequences.mantisWisdom(currentState, controls)
        controls = Sequences.driftKing(currentState, controls)
        controls = Sequences.patience(currentState, controls)
        controls = Sequences.haste(currentState, controls)

        controls.steer = steer_toward_target(my_car, target_location)
        
        #self.draw_debug(car_location, car_velocity, target_location, ball_location, ball_velocity, debugText)
        return controls

    def begin_front_flip(self, packet):
        # Send some quickchat just for fun
        self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Information_IGotIt)

        # Do a front flip. We will be committed to this for a few seconds and the bot will ignore other
        # logic during that time because we are setting the active_sequence.
        self.active_sequence = Sequences.frontFlip()

        # Return the controls associated with the beginning of the sequence so we can start right away.
        return self.active_sequence.tick(packet)

    def calculatePrediction(self, carPos, ballPos, ballSpeed, gameTime):
        # We're far away from the ball, let's try to lead it a little bit
        t=0
        ball_prediction = self.get_ball_prediction_struct()  # This can predict bounces, etc
        #ball_in_future = find_slice_at_time(ball_prediction, gameTime + ballSpeed.length()/2000)
        ball_in_future, t = find_matching_slice(ball_prediction, 0, self.getSlice)
        target = Vec3(ball_in_future.physics.location)

        self.renderer.draw_line_3d(ballPos, target, self.renderer.cyan())

        return target, t

    def draw_debug(self, carPos, carSpeed, target, ballPos, ballSpeed, corner_debug=None):
        self.renderer.draw_line_3d(carPos, target, self.renderer.white())
        self.renderer.draw_rect_3d(target, 8, 8, True, self.renderer.cyan(), centered=True)
        self.renderer.draw_line_3d(ballPos, ballPos+ballSpeed, self.renderer.red())
        self.renderer.draw_rect_3d(ballPos+ballSpeed, 8, 8, True, self.renderer.red(), centered=True)
        self.renderer.draw_line_3d(carPos, carPos+carSpeed, self.renderer.green())
        self.renderer.draw_rect_3d(carPos+carSpeed, 8, 8, True, self.renderer.green(), centered=True)
        self.renderer.draw_string_3d(carPos+carSpeed, 1, 1, f'Speed: {carSpeed.length():.1f}', self.renderer.white())
        # print the corner debug string
        # adjust y position depending on how many lines of text there are
        if corner_debug:
            corner_display_y = 700 - (corner_debug.count('\n') * 20)
            self.renderer.draw_string_2d(10, corner_display_y, 1, 1, corner_debug, self.renderer.white())

    def calculateDistance2D(vec1, vec2):
        return math.sqrt((vec1.x-vec2.x)**2+(vec1.y-vec2.y)**2)

    def getSlice(self, slice:Slice):
        isOnTheWall = abs(slice.physics.location.x) > 3900 or abs(slice.physics.location.y) > 5000 or (abs(slice.physics.location.x) > 3200 and abs(slice.physics.location.y) > 4500)
        isCloseToGroud = slice.physics.location.z < 100
        return isCloseToGroud or isOnTheWall

    def hip(self, vec:Vec3):
        return math.sqrt(vec.x**2+vec.y**2)