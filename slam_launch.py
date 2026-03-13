import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, TimerAction, IncludeLaunchDescription, RegisterEventHandler, LogInfo, EmitEvent
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from ros_gz_bridge.actions import RosGzBridge
from datetime import datetime


def generate_launch_description():
    # Start the Gazebo simulator:
    gz_sim = ExecuteProcess(
            cmd=["gz", "sim", "-r", "world.sdf"],
            output='screen'
        )

    # Launch bridges connecting Gazebo and ROS 2:
    bridge_node = RosGzBridge(
        bridge_name="bridge_node",
        config_file=os.path.join("configs", "bridge_config.yaml"),
        bridge_params=[{
            'qos_overrides./tf_static.publisher.durability': 'transient_local',
        }]
    )

    # Launch the traffic control node, which manages the states of traffic lights:
    traffic_ctrl_node = Node(
        package='traffic_ctrl',
        executable='traffic_ctrl_node',
        output='screen'
    )

    # Launch the keyboard listener node, 
    # which publishes car motions and saves SLAM map based on keyboard strikes:
    keyboard_listener_node = Node(
        package='keyboard_listener',
        executable='keyboard_listener_node',
        output='screen'
    )

    # Launch the SLAM Toolbox to generate a map from LiDAR data:
    slam_toolbox_launch_path = os.path.join(
        get_package_share_directory('slam_toolbox'),
        'launch',
        'online_async_launch.py'
    )
    
    slam_toolbox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(slam_toolbox_launch_path),
        launch_arguments={
            'use_sim_time': 'True',
            'slam_params_file': os.path.join("configs", "slam_config.yaml")
        }.items(),
    )
    
    # Launch the static transform publisher, 
    # which defines the coordinate transformation between the hatchback and the LiDAR:
    static_tf_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_pub_lidar',
        arguments=[
            '0', '0', '2.0',                   # x, y, z
            '0', '0', '0',                     # yaw, pitch, roll
            'base_link',                       # parent frame
            'hatchback/base_link/gpu_lidar'    # child frame
        ],
        parameters=[{'use_sim_time': True}]
    )

    # Launch RViz2 to visualize the generated map:
    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    # Sends a request to the Gazebo GUI to lock the camera onto the hatchback model.
    # Wrapped in a TimerAction to wait 20 seconds, giving the simulator time to initialize:
    follow_hatchback = ExecuteProcess(
        cmd=["gz", "service", "-s", "/gui/follow",
        "--reqtype", "gz.msgs.StringMsg",
        "--reptype", "gz.msgs.Boolean",
        "--timeout", "2000",
        "--req", "data: \"hatchback\""
        ]
    )

    follow_hatchback_timer = TimerAction(
        period=20.,
        actions=[follow_hatchback]
    )

    return LaunchDescription([
        rviz2_node, # Launch RViz2 before Gazebo so OS focuses on the Gazebo window.
        gz_sim,
        bridge_node,
        traffic_ctrl_node,
        keyboard_listener_node,
        slam_toolbox,
        static_tf_node,
        follow_hatchback_timer,
    ])