import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from slam_toolbox.srv import SaveMap
from std_msgs.msg import Int32, String
from geometry_msgs.msg import TwistStamped
from datetime import datetime
import os


class KeyboardListenerNode(Node):

  def __init__(self):
    super().__init__('keyboard_listener_node')
    self.keyboard_sub = self.create_subscription(
      Int32,
      '/keyboard/keypress',
      self.keyboard_callback,
      qos_profile=10)
    self.motion_pub = self.create_publisher(
      TwistStamped, 
      '/cmd_vel', 
      qos_profile=10)
    self.save_map_cli = self.create_client(SaveMap, '/slam_toolbox/save_map')
    self.KEY_DICT = {
      77: 'save_map', # key 's'
      87: 'forward',  # key 'up'
      88: 'backward', # key 'down'
      65: 'left',     # key 'left'
      68: 'right',    # key 'right'
      83: 'stop',     # key 'space'
    }
    self.MOTION_PROFILES = {
      'forward': {'lin': 3., 'ang': 0.},
      'backward': {'lin': -3., 'ang': 0.},
      'left': {'lin': 3., 'ang': 0.5},
      'right': {'lin': 3., 'ang': -0.5},
      'stop': {'lin': 0., 'ang': 0.},
    }

  def keyboard_callback(self, msg: Int32):
    key_idx = msg.data
    action = self.KEY_DICT.get(key_idx)
    if action is None:
      self.get_logger().info(f"Unrecognized key.")
    elif action == 'save_map':
      self.save_map()
    else:
      self.publish_motion(key_idx)
  
  def save_map(self):
    map_name = os.path.join("maps", f"map_{datetime.now().strftime('%m-%d-%y_%H:%M:%S')}")
    save_map_req = SaveMap.Request()

    name_msg = String()
    name_msg.data = map_name
    save_map_req.name = name_msg
    self.save_map_cli.call_async(save_map_req)
    self.get_logger().info(f"Saving current map to {map_name}.")
  
  def publish_motion(self, key_idx: int):
    out_msg = TwistStamped()
    out_msg.header.stamp = self.get_clock().now().to_msg()
    out_msg.header.frame_id = 'base_link'

    action = self.KEY_DICT[key_idx]
    out_msg.twist.linear.x = self.MOTION_PROFILES[action]['lin']
    out_msg.twist.angular.z = self.MOTION_PROFILES[action]['ang']
    self.motion_pub.publish(out_msg)
    self.get_logger().info(f"Motion published: {action}.")


def main(args=None):
  try:
    with rclpy.init(args=args):
      keyboard_listener_node = KeyboardListenerNode()

      rclpy.spin(keyboard_listener_node)
  except (KeyboardInterrupt, ExternalShutdownException):
    pass


if __name__ == '__main__':
  main()