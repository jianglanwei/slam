import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, TimerAction, IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ros_gz_bridge.actions import RosGzBridge


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

    # Launch RViz2 to visualize the SLAM map, and to input start and goal position:
    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    # Launch Nav2 for navigation:
    nav2_bringup_path = os.path.join(
        get_package_share_directory('nav2_bringup'),
        'launch',
        'bringup_launch.py'
    )

    map_arg = DeclareLaunchArgument(
        'map_file',
        default_value=os.path.join('maps', 'map_default.yaml'),
        description='Path to the map YAML file.'
    )

    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(nav2_bringup_path),
        launch_arguments={
            'use_sim_time': 'True',
            'params_file': os.path.join("configs", "nav_config.yaml"),
            'map': LaunchConfiguration('map_file'),
            'cmd_vel_topic': '/cmd_vel',
            'autostart': 'True',
            'use_composition': 'True'
        }.items()
    )

    nav2_bringup_timer = TimerAction(
        period=5.,
        actions=[nav2_bringup]
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
        period=15.,
        actions=[follow_hatchback]
    )


    return LaunchDescription([
        gz_sim,
        bridge_node,
        traffic_ctrl_node,
        static_tf_node,
        rviz2_node,
        map_arg,
        nav2_bringup_timer,
        follow_hatchback_timer,
    ])