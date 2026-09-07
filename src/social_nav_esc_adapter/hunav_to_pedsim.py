#!/usr/bin/env python3
"""Bridge HuNav /human_states → pedsim_msgs/AgentStates for ESC mapping.

ESC's world_modeler expects /pedsim_simulator/simulated_agents (Pedsim), not
HuNav Agents. Pedestrians stay on HuNav; this node is glue only.

Also broadcasts map→agent_<id> TF so ESC's optional lidar crop of people
can resolve frames if social_relevance_validity_checking is later enabled.
"""
from __future__ import annotations

import math

import rclpy
from geometry_msgs.msg import Quaternion, TransformStamped
from hunav_msgs.msg import Agent, Agents
from pedsim_msgs.msg import AgentForce, AgentState, AgentStates
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from tf2_ros import TransformBroadcaster


def _yaw_to_quat(yaw: float) -> Quaternion:
    return Quaternion(x=0.0, y=0.0, z=math.sin(yaw / 2.0), w=math.cos(yaw / 2.0))


class HunavToPedsim(Node):
    def __init__(self) -> None:
        super().__init__("hunav_to_pedsim")
        self.declare_parameter("in_topic", "/human_states")
        self.declare_parameter("out_topic", "/pedsim_simulator/simulated_agents")
        self.declare_parameter("stand_speed", 0.05)
        self.declare_parameter("publish_tf", True)

        in_topic = self.get_parameter("in_topic").get_parameter_value().string_value
        out_topic = self.get_parameter("out_topic").get_parameter_value().string_value
        self._stand = float(self.get_parameter("stand_speed").value)
        self._publish_tf = bool(self.get_parameter("publish_tf").value)

        self._pub = self.create_publisher(AgentStates, out_topic, 10)
        self._tf = TransformBroadcaster(self)
        self.create_subscription(Agents, in_topic, self._cb, 10)
        self.get_logger().info(f"{in_topic} → {out_topic}")

    def _cb(self, msg: Agents) -> None:
        out = AgentStates()
        out.header = msg.header
        if not out.header.frame_id:
            out.header.frame_id = "map"
        tfs: list[TransformStamped] = []

        for agent in msg.agents:
            if int(agent.type) == int(Agent.ROBOT):
                continue
            st = AgentState()
            st.header = msg.header
            st.header.frame_id = out.header.frame_id
            st.id = int(agent.id) if agent.id >= 0 else 0
            speed = float(agent.linear_vel)
            moving = speed > self._stand
            st.type = 1 if moving else 3
            st.social_state = (
                AgentState.TYPE_INDIVIDUAL_MOVING if moving else AgentState.TYPE_STANDING
            )
            st.pose = agent.position
            yaw = float(agent.yaw)
            st.pose.orientation = _yaw_to_quat(yaw)
            st.twist = agent.velocity
            if abs(st.twist.linear.x) < 1e-6 and abs(st.twist.linear.y) < 1e-6:
                st.twist.linear.x = speed * math.cos(yaw)
                st.twist.linear.y = speed * math.sin(yaw)
            st.twist.angular.z = float(agent.angular_vel)
            st.forces = AgentForce()
            out.agent_states.append(st)

            if self._publish_tf:
                tf = TransformStamped()
                tf.header = out.header
                tf.child_frame_id = f"agent_{st.id}"
                tf.transform.translation.x = st.pose.position.x
                tf.transform.translation.y = st.pose.position.y
                tf.transform.translation.z = st.pose.position.z
                tf.transform.rotation = st.pose.orientation
                tfs.append(tf)

        self._pub.publish(out)
        if tfs:
            self._tf.sendTransform(tfs)


def main() -> None:
    rclpy.init()
    try:
        rclpy.spin(HunavToPedsim())
    except (KeyboardInterrupt, ExternalShutdownException):
        pass


if __name__ == "__main__":
    main()
