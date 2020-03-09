#!/usr/bin/env python

#Jesus Tordesillas Torres, March 2020

import roslib
import rospy
import math
from snapstack_msgs.msg import QuadGoal, State
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from gazebo_msgs.msg import ModelState
import numpy as np
from numpy import linalg as LA

from tf.transformations import quaternion_from_euler, euler_from_quaternion

from pyquaternion import Quaternion
import tf
import math  



class GoalToCmdVel:

    def __init__(self):
        self.state=State()

        self.state.pos.x = rospy.get_param('~x', 0.0);
        self.state.pos.y = rospy.get_param('~y', 0.0);
        self.state.pos.z = rospy.get_param('~z', 0.0);

        self.state.quat.x = 0
        self.state.quat.y = 0
        self.state.quat.z = 0
        self.state.quat.w = 1

        self.current_yaw=0.0;



        #Publishers
        self.pubCmdVel = rospy.Publisher('jackal_velocity_controller/cmd_vel', Twist, queue_size=1, latch=True)
        self.pubState = rospy.Publisher('state', State, queue_size=1, latch=False)

        #Timers
        self.timer = rospy.Timer(rospy.Duration(0.1), self.cmdVelCB)

        self.kv =1.0
        self.kdist = 2.5#0.8
        self.kw =1.0
        self.kyaw = 2.0
        self.kalpha = 1.5

        self.state_initialized=False;
        self.goal_initialized=False;

        self.goal=QuadGoal()
        self.goal.pos.x=0.0;
        self.goal.pos.y=0.0;
        self.goal.pos.z=0.0;
        self.goal.vel.x=0.0;
        self.goal.vel.y=0.0;
        self.goal.vel.z=0.0;
        self.goal.accel.x=0.0;
        self.goal.accel.y=0.0;

        self.state_initialized=False;

    # def stateCB(self, msg):
    #     self.state.pos.x = msg.pos.x
    #     self.state.pos.y = msg.pos.y
    #     #self.pose.position.z = msg.pos.z
    #     self.state.quat.x = msg.quat.x
    #     self.state.quat.y = msg.quat.y
    #     self.state.quat.z = msg.quat.z
    #     self.state.quat.w = msg.quat.w

    #     self.state_initialized=True;

    def odomCB(self, msg):
        self.state.pos.x = msg.pose.pose.position.x
        self.state.pos.y = msg.pose.pose.position.y
        self.state.pos.z = msg.pose.pose.position.z

        (yaw, _, _)=euler_from_quaternion((msg.pose.pose.orientation.x,msg.pose.pose.orientation.y,msg.pose.pose.orientation.z,msg.pose.pose.orientation.w), "szyx")
        
        self.current_yaw = yaw;

        self.state.vel = msg.twist.twist.linear

        self.state.quat=msg.pose.pose.orientation;

        self.state.w = msg.twist.twist.angular

        self.pubState.publish(self.state)

        self.state_initialized=True;

    def goalCB(self, goal):

        self.goal=goal;

        # self.goal.pos.x=goal.pos.x;
        # self.goal.pos.y=goal.pos.y;
        # self.goal.pos.z=goal.pos.z;
        # self.goal.vel.x=goal.vel.x;
        # self.goal.vel.y=goal.vel.y;
        # self.goal.vel.z=goal.vel.z;
        # self.goal.accel.x=goal.accel.x;
        # self.goal.accel.y=goal.accel.y;

        self.goal_initialized=True;


    def cmdVelCB(self, goal):
        if (self.state_initialized==False or self.goal_initialized==False):
          return;

        x = self.goal.pos.x;
        y = self.goal.pos.y;
        xd = self.goal.vel.x;
        yd = self.goal.vel.y;
        xd2 = self.goal.accel.x;
        yd2 = self.goal.accel.y;


        v_desired = math.sqrt(xd**2 + yd**2);
        alpha = self.current_yaw - math.atan2(y - self.state.pos.y, x - self.state.pos.x);
        alpha=self.wrapPi(alpha)
        forward=1
        if(alpha <= 3.14 / 2.0 and alpha > -3.14 / 2.0):
          forward=1
        else:
          forward=-1

        dist_error = forward * math.sqrt( (x - self.state.pos.x)**2 + (y - self.state.pos.y)**2  );

        if (dist_error<0.03):
          alpha=0;

        numerator = xd * yd2 - yd * xd2;
        denominator = xd * xd + yd * yd;
        w_desired=0.0;
        if(denominator > 0.01):
          w_desired=numerator / denominator;

        desired_yaw=math.atan2(yd,xd);

        yaw_error = self.current_yaw - desired_yaw;
        yaw_error=self.wrapPi(yaw_error)


        twist=Twist();

        twist.linear.x = self.kv * v_desired + self.kdist * dist_error;
        twist.angular.z = self.kw * w_desired - self.kyaw * yaw_error - self.kalpha * alpha;

        # twist.linear.x=self.Kp*(goal.pos.x - self.state.pos.x);

        self.pubCmdVel.publish(twist)


    def wrapPi(self, x):
        x=(x+np.pi) % (2 * np.pi)
        if(x<0):
            x=x+2 * np.pi
        return x-np.pi   



def startNode():
    c = GoalToCmdVel()

    #Subscribers
    #self.sub_state = rospy.Subscriber("state", State, self.stateCB, queue_size=1)

    rospy.Subscriber("goal", QuadGoal, c.goalCB, queue_size=1)
    rospy.Subscriber("ground_truth/state", Odometry, c.odomCB, queue_size=1) #jackal_velocity_controller/odom   # odometry/local_filtered


    rospy.spin()

if __name__ == '__main__':

    ns = rospy.get_namespace()
    try:
        rospy.init_node('goal_to_cmd_vel')
        if str(ns) == '/':
            rospy.logfatal("Need to specify namespace as vehicle name.")
            rospy.logfatal("This is tyipcally accomplished in a launch file.")
            rospy.logfatal("Command line: ROS_NAMESPACE=mQ01 $ rosrun quad_control joy.py")
        else:
            print "Starting goal_to_cmd node for: " + ns
            startNode()
    except rospy.ROSInterruptException:
        pass
