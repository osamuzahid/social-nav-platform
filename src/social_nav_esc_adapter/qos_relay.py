#!/usr/bin/env python3
"""Relay Isaac BEST_EFFORT sensors to RELIABLE topics for ESC.

Stretch /odom is BEST_EFFORT (Nav2 sensor QoS). ESC mapper/planner/controller
subscribe with default RELIABLE and otherwise never see odom, so the mapper
blocks forever on 'Waiting for odometry' and then exits. RTX /scan is the
same mismatch for message_filters.

Stamps and frames are copied unchanged.
"""
from __future__ import annotations

import argparse
import importlib

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy


def _load_msg(type_name: str):
    # sensor_msgs/msg/LaserScan → sensor_msgs.msg.LaserScan
    pkg, kind, name = type_name.split("/")
    if kind != "msg":
        raise ValueError(f"expected pkg/msg/Type, got {type_name}")
    mod = importlib.import_module(f"{pkg}.msg")
    return getattr(mod, name)


class QosRelay(Node):
    def __init__(self, msg_type, in_topic: str, out_topic: str, node_name: str) -> None:
        super().__init__(node_name)
        be = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        rel = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self._pub = self.create_publisher(msg_type, out_topic, rel)
        self.create_subscription(msg_type, in_topic, self._cb, be)
        self.get_logger().info(f"BEST_EFFORT {in_topic} → RELIABLE {out_topic}")

    def _cb(self, msg) -> None:
        self._pub.publish(msg)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-topic", required=True)
    ap.add_argument("--out-topic", required=True)
    ap.add_argument("--type", required=True, help="pkg/msg/Type e.g. nav_msgs/msg/Odometry")
    ap.add_argument(
        "--node-name",
        default="esc_qos_relay",
        help="unique ROS node name (odom + scan relays run in parallel)",
    )
    args = ap.parse_args()

    rclpy.init()
    msg_type = _load_msg(args.type)
    try:
        rclpy.spin(QosRelay(msg_type, args.in_topic, args.out_topic, args.node_name))
    except (KeyboardInterrupt, ExternalShutdownException):
        pass


if __name__ == "__main__":
    main()
