#!/usr/bin/env python3
"""Send a plaza goal to ESC via PoseStamped (Goto2D action is commented out).

ESC humble-devel planner subscribes to query_goal_topic
(default /esc_move_base_planner/query_goal). The Goto2D action server is
not started. Publish a few times so a late subscriber still sees it.

With --wait, spin until /goal_reached or XY near the goal, or timeout.
"""
from __future__ import annotations

import argparse
import math
import sys
import time

import rclpy
from geometry_msgs.msg import PoseStamped, Quaternion
from nav_msgs.msg import Odometry
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool


def _quat(yaw: float) -> Quaternion:
    return Quaternion(x=0.0, y=0.0, z=math.sin(yaw / 2.0), w=math.cos(yaw / 2.0))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--x", type=float, default=1.5)
    ap.add_argument("--y", type=float, default=6.5)
    ap.add_argument("--yaw", type=float, default=1.57)
    ap.add_argument("--frame", default="map")
    ap.add_argument("--topic", default="/esc_move_base_planner/query_goal")
    ap.add_argument("--reached-topic", default="/goal_reached")
    ap.add_argument("--odom-topic", default="/odom_esc")
    ap.add_argument("--xy-tol", type=float, default=0.45)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--wait", action="store_true")
    ap.add_argument(
        "--timeout",
        type=float,
        default=240.0,
        help="Wall-clock seconds while --wait. <=0 waits until goal_reached / xy-tol only.",
    )
    args = ap.parse_args()

    rclpy.init()
    node = rclpy.create_node("send_esc_goal")
    pub = node.create_publisher(PoseStamped, args.topic, 10)

    msg = PoseStamped()
    msg.header.frame_id = args.frame
    msg.pose.position.x = args.x
    msg.pose.position.y = args.y
    msg.pose.orientation = _quat(args.yaw)

    def _publish() -> None:
        msg.header.stamp = node.get_clock().now().to_msg()
        pub.publish(msg)

    for _ in range(max(1, args.repeats)):
        _publish()
        rclpy.spin_once(node, timeout_sec=0.2)
        time.sleep(0.15)
    print(f"sent query_goal ({args.x},{args.y}) yaw={args.yaw} → {args.topic}", flush=True)

    if not args.wait:
        node.destroy_node()
        rclpy.shutdown()
        return 0

    reached = {"flag": False}
    odom_xy = {"xy": None}

    def on_reached(m: Bool) -> None:
        if m.data:
            reached["flag"] = True

    def on_odom(m: Odometry) -> None:
        odom_xy["xy"] = (m.pose.pose.position.x, m.pose.pose.position.y)

    node.create_subscription(Bool, args.reached_topic, on_reached, 10)
    node.create_subscription(
        Odometry,
        args.odom_topic,
        on_odom,
        QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        ),
    )

    t0 = time.time()
    last_pub = t0
    # timeout <= 0: hospital ESC long detour — only goal_reached / xy-tol ends the wait.
    deadline = None if args.timeout <= 0.0 else (t0 + args.timeout)
    while rclpy.ok() and (deadline is None or time.time() < deadline):
        now = time.time()
        # Planner may not be spinning yet when the first burst is sent (node
        # exists during ctor). Keep republishing; PoseStamped is volatile.
        if now - last_pub >= 1.0:
            _publish()
            last_pub = now
        rclpy.spin_once(node, timeout_sec=0.2)
        if reached["flag"]:
            print("GOAL=SUCCEEDED (goal_reached)", flush=True)
            node.destroy_node()
            rclpy.shutdown()
            return 0
        xy = odom_xy["xy"]
        if xy is not None:
            d = math.hypot(xy[0] - args.x, xy[1] - args.y)
            if d <= args.xy_tol:
                print(f"GOAL=SUCCEEDED (xy={xy[0]:.2f},{xy[1]:.2f} d={d:.3f})", flush=True)
                node.destroy_node()
                rclpy.shutdown()
                return 0

    xy = odom_xy["xy"]
    print(f"GOAL=TIMEOUT xy={xy} after {args.timeout:.0f}s", flush=True)
    node.destroy_node()
    rclpy.shutdown()
    return 1


if __name__ == "__main__":
    sys.exit(main())
