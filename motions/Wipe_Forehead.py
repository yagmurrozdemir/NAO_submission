#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Wipe_Forehead.py

import sys
import time
from naoqi import ALProxy


def main(robotIP, port):
    motion = ALProxy("ALMotion", robotIP, port)
    posture = ALProxy("ALRobotPosture", robotIP, port)

    # Go to a safe posture
    posture.goToPosture("StandInit", 0.5)

    # Simple wipe-forehead-like motion
    names = ["RShoulderPitch", "RShoulderRoll"]
    angles_up = [0.0, -0.3]    # arm up/out a bit
    angles_down = [1.4, 0.2]   # back to relaxed
    speed = 0.25

    # Faster upward motion
    motion.setAngles(names, angles_up, speed)
    time.sleep(1.0)

    # Faster return
    motion.setAngles(names, angles_down, speed)
    time.sleep(1.5)


if __name__ == "__main__":
    robotIP = "127.0.0.1"
    port = 9559

    if len(sys.argv) >= 2:
        robotIP = sys.argv[1]
    if len(sys.argv) >= 3:
        port = int(sys.argv[2])

    main(robotIP, port)
