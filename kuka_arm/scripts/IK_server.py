#!/usr/bin/env python

# Copyright (C) 2017 Udacity Inc.
#
# This file is part of Robotic Arm: Pick and Place project for Udacity
# Robotics nano-degree program
#
# All Rights Reserved.

# Author: Harsh Pandya

# import modules
import rospy
import tf
from kuka_arm.srv import *
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from geometry_msgs.msg import Pose
from mpmath import *
from sympy import *
import numpy as np
from numpy import array
from sympy import   symbols, cos, sin, pi, sqrt, atan2  

#### Transformation matrix function###
def Transform(q,d,a,alpha,s):
	T = Matrix([[cos(q)             , -sin(q)            ,  0         , a              ],
	[sin(q) * cos(alpha), cos(q) * cos(alpha), -sin(alpha), -sin(alpha) * d],
	[sin(q) * sin(alpha), cos(q) * sin(alpha),  cos(alpha),  cos(alpha) * d ],
	[0                  , 0                  ,  0         ,  1              ]])
	return T.subs(s)
######################################


def handle_calculate_IK(req):
    rospy.loginfo("Received %s eef-poses from the plan" % len(req.poses))
    if len(req.poses) < 1:
        print "No valid poses received"
        return -1
    else:

        
    # Create symbols
	q1,q2,q3,q4,q5,q6,q7 = symbols('q1:8')
	d1,d2,d3,d4,d5,d6,d7 = symbols('d1:8')
	a0,a1,a2,a3,a4,a5,a6 = symbols('a0:6')
	alpha0,alpha1,alpha2,alpha3,alpha4,alpha5,alpha6 = symbols('alpha0:7')
	################


	# Create Modified DH parameters
	s = {alpha0:       0, a0:      0,    d1:  0.75,
	     alpha1:   -90.0, a1:   0.35,    d2:     0, q2: q2-90.0,
	     alpha2:       0, a2:   1.25,    d3:     0,
	     alpha3:   -90.0, a3: -0.054,    d4:   1.5,
	     alpha4:    90.0, a4:      0,    d5:     0,
	     alpha5:   -90.0, a5:      0,    d6:     0,
	     alpha6:       0, a6:      0,    d7: 0.303, q7: 0}
	################################
	
	# Create individual transformation matrices
	T0_1=Transform(q1,d1,a0,alpha0,s)
	T1_2=Transform(q2,d2,a1,alpha1,s)
	T2_3=Transform(q3,d3,a2,alpha2,s)
	T3_4=Transform(q4,d4,a3,alpha3,s)
	T4_5=Transform(q5,d5,a4,alpha4,s)
	T5_6=Transform(q6,d6,a5,alpha5,s)
	T6_G=Transform(q7,d7,a6,alpha6,s)
	T0_G= T0_1*T1_2*T2_3*T3_4*T4_5*T5_6*T6_G
	###########################################

	# Creating function for Rotation matrices
	R,P,Y = symbols('R P Y')
	def Rot(symb,Roll=R,Pitch=P,Yaw=Y):
		if symb == 'R':

			Rot = Matrix([
			            [   1,      0,       0],
			            [   0, cos(Roll), -sin(Roll)],
			            [   0, sin(Roll),  cos(Roll)]]) 
		elif symb == 'P':
			Rot = Matrix([
			            [ cos(Pitch), 0, sin(Pitch)],
			            [      0, 1,      0],
			            [-sin(Pitch), 0, cos(Pitch)]])  
		elif symb == 'Y':
			Rot = Matrix([
			            [cos(Yaw), -sin(Yaw), 0],
			            [sin(Yaw),  cos(Yaw), 0],
			            [     0,       0, 1]])  

		return Rot
    #######################################


    # Accounting for Orientation Difference 
    Rot_x = Rot('R')
    Rot_y = Rot('P')
    Rot_z = Rot('Y')
    Rot_F = Rot_z.subs(Y,radians(180))*Rot_Y.subs(P,radians(-90))
    Rot_E = Rot_z*Rot_y*Rot_x
    Rot_EE = Rot_E * Rot_F
    #######################################



        # Initialize service response
    joint_trajectory_list = []
    for x in xrange(0, len(req.poses)):
        # IK code starts here
        joint_trajectory_point = JointTrajectoryPoint()

    # Extract end-effector position and orientation from request
    # px,py,pz = end-effector position
    # roll, pitch, yaw = end-effector orientation
        px = req.poses[x].position.x
        py = req.poses[x].position.y
        pz = req.poses[x].position.z

        (roll, pitch, yaw) = tf.transformations.euler_from_quaternion(
            [req.poses[x].orientation.x, req.poses[x].orientation.y,
                req.poses[x].orientation.z, req.poses[x].orientation.w])

        
    # Finding the position of WC according to End Effector
	Rot_EE.subs({'R':roll , 'P':pitch , 'Y':yaw})
	Pos_EE = Matrix([px,py,pz])
	Pos_WC = Pos_EE - 0.303*Rot_EE[:,2]
	WC_x = Pos_WC[0]
	WC_y = Pos_WC[1]
	WC_z = Pos_WC[2]


	# Calculate joint angles using Geometric IK method
	La = 1.502 
	Lc = 1.25
	a1 = 0.35
	d1 = 0.75
	Lxy= sqrt(pow(WC_x, 2.) + pow(WC_y, 2.) ) - a1
	Lz = WC_z - d1
	Lb = sqrt(pow(Lxy, 2.) + pow(Lz, 2.))
    

    a_ang = acos( ( pow(Lb, 2.) + pow(Lc, 2.) - pow(La, 2.)) / (2. * Lb * Lc) )
    b_ang = acos( ( pow(La, 2.) + pow(Lc, 2.) - pow(Lb, 2.)) / (2. * La * Lc) )
    c_ang = acos( ( pow(La, 2.) + pow(Lb, 2.) - pow(Lc, 2.)) / (2. * La * Lb) )

    ### Finding Theta 1,2,3
    theta1 = atan2(WC_y , WC_x)
    theta2 = 90. - a_ang - atan2(Lz/Lxy)
    theta3 = 90. - Lb - atan2(0.054/1.5)
    #######################

    # Evaluating Transformation from 0 to 3
    R0_3 = (T0_1 * T1_2 * T2_3).evalf(subs={theta1: theta1,theta2: theta2,theta3: theta3})[0:3, 0:3]
    #######################################


    # Evaluating Transformation from 3 to 6
    R3_6 = R0_3.T * R_EE
    theta4 = atan2(R3_6[2,2], -R3_6[0,2])
    theta5 = atan2(sqrt(pow(R3_6[0,2], 2) + pow(R3_6[2,2], 2)), R3_6[1,2])
    theta6 = atan2(-R3_6[1,1], R3_6[1,0])
    #######################################


        # Populate response for the IK request
        # In the next line replace theta1,theta2...,theta6 by your joint angle variables
    joint_trajectory_point.positions = [theta1, theta2, theta3, theta4, theta5, theta6]
    joint_trajectory_list.append(joint_trajectory_point)

    rospy.loginfo("length of Joint Trajectory List: %s" % len(joint_trajectory_list))
    return CalculateIKResponse(joint_trajectory_list)


def IK_server():
    # initialize node and declare calculate_ik service
    rospy.init_node('IK_server')
    s = rospy.Service('calculate_ik', CalculateIK, handle_calculate_IK)
    print "Ready to receive an IK request"
    rospy.spin()

if __name__ == "__main__":
    IK_server()
