from States import State
from util.sequence import Sequence, ControlStep
from util.vec import Vec3
from util.orientation import Orientation
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import BoostPadState

def frontFlip():
    return Sequence([
            ControlStep(duration=0.3, controls=SimpleControllerState(jump=True,pitch=1)),
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, pitch=-1)),
            ControlStep(duration=0.8, controls=SimpleControllerState()),])

def doubleJump():
    return Sequence([
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.01, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.2, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.8, controls=SimpleControllerState()),])

def catReflexes(currentState:State , controls:SimpleControllerState) -> SimpleControllerState:
    if currentState.shouldAdjustInAir():
        if currentState.carRotation.roll > 1:
            controls.roll = -1
        elif currentState.carRotation.roll < -1:
            controls.roll = 1
        elif currentState.carRotation.roll > 0.1 or currentState.carRotation.roll < -0.1:
            controls.roll = -currentState.carRotation.roll
        
        if currentState.carRotation.pitch > 1:
            controls.pitch = -1
        elif  currentState.carRotation.pitch < -1:
            controls.pitch = 1
        elif  currentState.carRotation.pitch > 0.1 or currentState.carRotation.pitch < -0.1:
            controls.pitch = -currentState.carRotation.pitch
    
    return controls

def mantisWisdom(currentState:State , controls:SimpleControllerState) -> SimpleControllerState:
    if currentState.shouldJump():
        controls.jump = True
    else:
        controls.jump = False

    return controls
    
def patience(currentState:State , controls:SimpleControllerState) -> SimpleControllerState:
    if currentState.shouldBreak() and currentState.carVelocity.length() > 0:
        controls.throttle = -1
    else:
        controls.throttle = 1

    return controls

def haste(currentState:State , controls:SimpleControllerState) -> SimpleControllerState:
    if currentState.shouldUseBoost():
        controls.boost = True
    else:
        controls.boost = False

    return controls

def driftKing(currentState:State , controls:SimpleControllerState) -> SimpleControllerState:
    if currentState.shouldDrift():
        controls.handbrake = True
    else:
        controls.handbrake= False

    return controls

def striker(currentState:State , target:Vec3) -> Vec3:
    return currentState.driveBallToGoal(target)

def goalie(currentState:State , target:Vec3) -> Vec3:
    return currentState.driveToOwnGoal(target)

def boostManagement(currentState:State, boostPadList:BoostPadState, target:Vec3) -> Vec3:
    return currentState.shouldGoGetBoost(boostPadList, target)

