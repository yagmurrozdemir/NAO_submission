#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Hello.py

import sys
import time
from naoqi import ALProxy


def main(robotIP, port):
    motion = ALProxy("ALMotion", robotIP, port)
    posture = ALProxy("ALRobotPosture", robotIP, port)

    # Go to a safe initial posture
    posture.goToPosture("StandInit", 0.5)

    # Simple wave with right arm
    names = ["RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll"]
    angles_raise = [0.0, -0.4, 1.5, 1.0]
    speed = 0.25

    # Raise arm (faster than before)
    motion.setAngles(names, angles_raise, speed)
    time.sleep(0.8)

    # Two quick waves (faster timing)
    for _ in range(2):
        motion.setAngles(["RElbowRoll"], [0.2], 0.4)
        time.sleep(0.3)
        motion.setAngles(["RElbowRoll"], [1.0], 0.4)
        time.sleep(0.3)

    # Lower arm back
    angles_down = [1.4, 0.2, 1.2, 0.0]
    motion.setAngles(names, angles_down, speed)
    time.sleep(1.0)


if __name__ == "__main__":
    robotIP = "127.0.0.1"
    port = 9559

    if len(sys.argv) >= 2:
        robotIP = sys.argv[1]
    if len(sys.argv) >= 3:
        port = int(sys.argv[2])

    main(robotIP, port)
