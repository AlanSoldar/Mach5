from rlbot.utils.structures.game_data_struct import PlayerInfo, BoostPadState
from util.drive import  relativeDirection
from util.vec import Vec3
from util.orientation import Orientation, relative_location
from util.Localizator import getBoostPadLocation, getOrangeGoalCenter, getBlueGoalCenter
import math

class State:

    def __init__(self, car:PlayerInfo, ballPos:Vec3, ballVelocity:Vec3, target:Vec3, t:int, renderer):
        self.carPos = Vec3(car.physics.location)
        self.carVelocity = Vec3(car.physics.velocity)
        self.carRotation = Orientation(car.physics.rotation)
        self.carBoost = car.boost
        self.jumped = car.jumped
        self.hasWheelContact = car.has_wheel_contact
        self.ballPos = ballPos
        self.ballVelocity = ballVelocity
        self.team = car.team
        self.target = target
        self.timeToTarget = t/60
        self.renderer = renderer

    def flipToGetSpeed(self):
        isTooFar = self.carPos.dist(self.target) > 1000
        isCloseEnough = self.carPos.dist(self.target) < 200
        isAtRightDistance = isTooFar or isCloseEnough
        return self.carBoost < 1 and self.shouldUseBoost() and self.carVelocity.length() > 1000 and self.isGroundLevel() and isAtRightDistance and False

    def shouldJump(self):
        isSideways = 1.0 < self.carRotation.roll or self.carRotation.roll < -1.0
        isOnAWall = self.hasWheelContact and isSideways and self.carPos.z > 800 and not self.jumped
        
        ballIsOverHead = calculateDistance2D(self.carPos,self.ballPos) < 150 and self.ballPos.z - self.carPos.z > 200
        ballIsReacheable = self.ballPos.z - self.carPos.z < 500

        justJumped = self.jumped and not self.hasWheelContact
        jumpWillReachBall = ballIsOverHead and ballIsReacheable
        doubleJumpWillReachBall = ballIsOverHead and ballIsReacheable and justJumped and self.carRotation.roll < 0.1


        return jumpWillReachBall or doubleJumpWillReachBall or isOnAWall

    def isGroundLevel(self):
        isOndTheGround = self.carPos.z < 30
        isUpsideUp = -0.05 < self.carRotation.roll < 0.05

        return isOndTheGround and isUpsideUp

    def shouldUseBoost(self):
        isFarFromTarget = calculateDistance2D(self.carPos, self.target) > 100
        willNotReachTargetInTime = self.timeToTargetAtCurrentSpeed() > self.timeToTarget 
        isTooSlow = 300 < self.carVelocity.length() < 2200
        isFacingTarget = self.isInsideCone(self.target, 0.3)
        needSpeed = (isTooSlow or willNotReachTargetInTime) and isFacingTarget
        #haveBoost = self.carBoost > 0

        needToGoToBallSide = calculateDistance2D(self.carPos, self.ballPos) < 400 and 0 < calculateDistance2D(self.target, self.ballPos) < 40 and calculateDistance2D(self.ballVelocity, self.carVelocity) > 200
        canGetCloserToTarget = isFarFromTarget and needSpeed

        print(canGetCloserToTarget, needToGoToBallSide)

        return canGetCloserToTarget or needToGoToBallSide

    def shouldDrift(self):
        return not self.isInsideCone(self.target, 1.5) and self.carVelocity.length() > 1000

    def shouldAdjustInAir(self):
        isCarInTheAir = not self.hasWheelContact
        isUpsideUp = (-0.1 < self.carRotation.pitch < 0.1) and -0.1 < self.carRotation.roll < 0.1

        return isCarInTheAir and not isUpsideUp

    def shouldBreak(self):
        needToSlowDown = self.timeToTarget > 0 and self.isGoingForward() and self.timeToTargetAtCurrentSpeed() < self.timeToTarget 
        isDribbling = calculateDistance2D(self.carPos, self.ballPos) < 25

        #print(calculateDistance2D(self.carPos, self.ballPos))

        return needToSlowDown or isDribbling

    def driveBallToGoal(self, target:Vec3):
        goal = getOrangeGoalCenter() if self.team == 0 else getBlueGoalCenter()
        ownGoal = getBlueGoalCenter() if self.team == 0 else getOrangeGoalCenter()
        goal.z = 0
        BallToGoal = goal-self.ballPos

        deviation = (BallToGoal)/50
        deviation = saturateVec(deviation, 100)
        return target - deviation


    def driveToOwnGoal(self, target:Vec3):
        goal = getOrangeGoalCenter() if self.team == 0 else getBlueGoalCenter()
        ownGoal = getBlueGoalCenter() if self.team == 0 else getOrangeGoalCenter()
        goal.z = 0
        ownGoal.z = 0
        isBallGoingTowardsOwnGoal = self.ballVelocity.dot(ownGoal) > 0
        isBallCloserToOwnGoal = self.ballPos.dist(ownGoal) + 300 < self.carPos.dist(ownGoal) 

        if isBallGoingTowardsOwnGoal and isBallCloserToOwnGoal:
            return ownGoal

        return target

    def shouldGoGetBoost(self, boostPadState:BoostPadState, target:Vec3):
        boostPadList = getBoostPadLocation()
        for i in range(len(boostPadList)):
            isCloserToBoost = calculateDistance2D(self.carPos, boostPadList[i]) < calculateDistance2D(self.carPos, target) 
            isFarFromTarget = calculateDistance2D(self.carPos, target) > 500
            isFarFromBall = calculateDistance2D(self.carPos, self.ballPos) > 500
            isLightDeviation = self.isInsideCone(boostPadList[i], 0.5) and self.isInsideCone(target, 0.5) and calculateDistance2D(self.carPos, boostPadList[i]) < 600
            if boostPadState[i].is_active and isFarFromTarget and isFarFromBall and isCloserToBoost and isLightDeviation and self.carBoost < 60:
                return boostPadList[i]

        return target

    def isGoingForward(self):
        xMax = abs(self.carRotation.forward.x) + abs(self.carVelocity.x)
        yMax = abs(self.carRotation.forward.y) + abs(self.carVelocity.y)
        xCurrent = abs(self.carRotation.forward.x + self.carVelocity.x)
        yCurrent = abs(self.carRotation.forward.y + self.carVelocity.y)
        return xMax == xCurrent and yMax == yCurrent

    def timeToTargetAtCurrentSpeed(self):
        if(self.carVelocity.length() > 0):
            return self.carPos.dist(self.target)/self.carVelocity.length()
        else:
            return 1000

    def isInsideCone(self, target, size):
        return -size < relativeDirection(self.carPos, self.carRotation, target) < size

def calculateDistance2D(vec1:Vec3, vec2:Vec3):
    return math.sqrt((vec1.x-vec2.x)**2+(vec1.y-vec2.y)**2)

def saturateVec(vec:Vec3, saturation:int):
    if vec.x > saturation:
        vec.x = saturation
    if vec.y > saturation:
        vec.y = saturation
    if vec.z > saturation:
        vec.z = saturation

    return vec
