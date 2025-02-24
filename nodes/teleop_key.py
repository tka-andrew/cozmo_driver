#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
This file implements a ROS keyboard teleoperation node for the ANKI Cozmo robot.

Keyboard mapping:

w - forward
a - backward
s - turn left
d - turn right

r - head up
f - head normal position
v - head down

t - lift up
t - lift normal position
t - lift down

Copyright {2017} {Peter Rudolph}

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import rospy
import sys
import tty
import termios
import atexit
from select import select
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64

MIN_HEAD_ANGLE = -25.0
MAX_HEAD_ANGLE = 44.5
STD_HEAD_ANGLE = 20.0
SUM_HEAD_ANGLE = MAX_HEAD_ANGLE - MIN_HEAD_ANGLE

MIN_LIFT_HEIGHT = 32.0
MAX_LIFT_HEIGHT = 92.0
STD_LIFT_HEIGHT = 32.0
SUM_LIFT_HEIGHT = MAX_LIFT_HEIGHT - MIN_LIFT_HEIGHT

HEAD_ADJUSTMENT_RATE = 2.0
LIFT_ADJUSTMENT_RATE = 2.0


class CozmoTeleop(object):
    """
    Class providing keyboard teleoperation functionality for Cozmo robot.

    """

    settings = None

    def __init__(self):
        # setup
        CozmoTeleop.settings = termios.tcgetattr(sys.stdin)
        atexit.register(self.reset_terminal)

        # vars
        self.head_angle = STD_HEAD_ANGLE
        self.lift_height = STD_LIFT_HEIGHT

        # params
        self.lin_vel = rospy.get_param('~lin_vel', 0.2)
        self.ang_vel = rospy.get_param('~ang_vel', 1.5757)

        # pubs
        self._head_pub = rospy.Publisher('head_angle', Float64, queue_size=1)
        self._lift_pub = rospy.Publisher('lift_height', Float64, queue_size=1)
        self._cmd_vel_pub = rospy.Publisher('cmd_vel', Twist, queue_size=1)

    def get_key(self):
        """
        Get the latest keyboard input.

        :rtype: char
        :returns: The key pressed.
        """
        self.set_terminal()
        select([sys.stdin], [], [], 0)
        key = sys.stdin.read(1)
        self.reset_terminal()
        return key

    @staticmethod
    def set_terminal():
        """
        Set the terminal to raw state.

        """
        tty.setraw(sys.stdin.fileno())

    @staticmethod
    def reset_terminal():
        """
        Reset the terminal to state before class initialization.

        """
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, CozmoTeleop.settings)

    def run(self):
        """
        The keyboard capture loop.

        """
        r = rospy.Rate(20)

        while not rospy.is_shutdown():

            # reset twist (commanded velocities)
            cmd_vel = Twist()

            # reset states
            head_changed = False
            lift_changed = False

            # get key
            key = self.get_key()

            # ctrl+c
            if key == '\x03': # Ctrl + C
                print('Shutdown')
                break

            # robot
            # w - forward
            elif key == 'w':
                cmd_vel.linear.x = self.lin_vel
            # s - backward
            elif key == 's':
                cmd_vel.linear.x = -self.lin_vel
            # a - turn left
            elif key == 'a':
                cmd_vel.angular.z = self.ang_vel
            # d - turn right
            elif key == 'd':
                cmd_vel.angular.z = -self.ang_vel

            # head movement
            # r - up
            elif key =='r':
                self.head_angle += HEAD_ADJUSTMENT_RATE
                if self.head_angle > MAX_HEAD_ANGLE:
                    self.head_angle = MAX_HEAD_ANGLE
                head_changed = True
            # f - center
            elif key == 'f':
                self.head_angle = STD_HEAD_ANGLE
                head_changed = True
            # v - down
            elif key == 'v':
                self.head_angle -= HEAD_ADJUSTMENT_RATE
                if self.head_angle < MIN_HEAD_ANGLE:
                    self.head_angle = MIN_HEAD_ANGLE
                head_changed = True

            # lift movement
            # t - up
            elif key == 't':
                self.lift_height += LIFT_ADJUSTMENT_RATE
                if self.lift_height > MAX_LIFT_HEIGHT:
                    self.lift_height = MAX_LIFT_HEIGHT
                lift_changed = True
            # g - center
            elif key == 'g':
                self.lift_height = STD_LIFT_HEIGHT
                lift_changed = True
            # b - down
            elif key == 'b':
                self.lift_height -= LIFT_ADJUSTMENT_RATE
                if self.lift_height < MIN_LIFT_HEIGHT:
                    self.lift_height = MIN_LIFT_HEIGHT
                lift_changed = True

            # publish commands (head angle and lift height on change only)
            self._cmd_vel_pub.publish(cmd_vel)
            if head_changed:
                self._head_pub.publish(data=self.head_angle)
            if lift_changed:
                self._lift_pub.publish(data=(self.lift_height-MIN_LIFT_HEIGHT)/SUM_LIFT_HEIGHT)

            r.sleep()

# start ROS node
rospy.init_node('cozmo_teleop_key')
# initialize keyboard teleoperation
cozmo_teleop = CozmoTeleop()
# loop
cozmo_teleop.run()
