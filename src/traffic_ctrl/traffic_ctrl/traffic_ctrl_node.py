import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from rosgraph_msgs.msg import Clock
from ros_gz_interfaces.msg import MaterialColor, Entity
import time


class TrafficCtrlNode(Node):

  def __init__(self):
    super().__init__('traffic_ctrl_node')
    self.subscription = self.create_subscription(
      Clock,
      '/clock',
      self.clock_callback,
      qos_profile=10)
    self.publisher_ = self.create_publisher(
      MaterialColor, 
      '/material_color', 
      qos_profile=500)
    self.glow_color = {"a": "red", "b": "green"} # initial light sequence.
    self.LIGHT_DICT = {
      "light_nw_n": "a", "light_nw_s": "a", "light_nw_w": "b", "light_nw_e": "b",
      "light_ne_n": "b", "light_ne_s": "b", "light_ne_w": "a", "light_ne_e": "a",
      "light_sw_n": "b", "light_sw_s": "b", "light_sw_w": "a", "light_sw_e": "a",
      "light_se_n": "a", "light_se_s": "a", "light_se_w": "b", "light_se_e": "b",
    }
    self.RGBA = {"red": (1., 0., 0., 1.),
                 "yellow": (1., 0.75, 0., 1.),
                 "green": (0., 1., 0., 1.)}
    self.SIGNAL_LOOP_DURATION = 20
    self.YELLOW_LIGHT_DURATION = 3
    self.publish_color()

  def clock_callback(self, msg: Clock):
    if msg.clock.sec == 0: 
      return
    if msg.clock.nanosec != 0:
      return
    current_phase_time = msg.clock.sec % self.SIGNAL_LOOP_DURATION
    if current_phase_time == 0:
      self.glow_color = {"a": "red", "b": "green"}
      self.publish_color()
    elif current_phase_time == self.SIGNAL_LOOP_DURATION // 2 - self.YELLOW_LIGHT_DURATION:
      self.glow_color = {"a": "red", "b": "yellow"}
      self.publish_color()
    elif current_phase_time == self.SIGNAL_LOOP_DURATION // 2:
      self.glow_color = {"a": "green", "b": "red"}
      self.publish_color()
    elif current_phase_time == self.SIGNAL_LOOP_DURATION - self.YELLOW_LIGHT_DURATION:
      self.glow_color = {"a": "yellow", "b": "red"}
      self.publish_color()

  def publish_color(self):
    for name, group in self.LIGHT_DICT.items():
      for color in self.RGBA.keys():
        out_msg = MaterialColor()
        out_msg.entity.type = Entity.VISUAL
        out_msg.entity.name = f"stoplights::{name}::link::{color}_{group}"
        if color == self.glow_color[group]:
          out_msg.emissive.r = self.RGBA[color][0]
          out_msg.emissive.g = self.RGBA[color][1]
          out_msg.emissive.b = self.RGBA[color][2]
          out_msg.emissive.a = self.RGBA[color][3]
        else:
          out_msg.emissive.r = 0.
          out_msg.emissive.g = 0.
          out_msg.emissive.b = 0.
          out_msg.emissive.a = 1.
        self.publisher_.publish(out_msg)
      time.sleep(0.001)
    self.get_logger().info(f"Traffic light signal published: {self.glow_color}.")


def main(args=None):
  try:
    with rclpy.init(args=args):
      traffic_ctrl_node = TrafficCtrlNode()

      rclpy.spin(traffic_ctrl_node)
  except (KeyboardInterrupt, ExternalShutdownException):
    pass


if __name__ == '__main__':
  main()