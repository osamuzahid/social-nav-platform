FROM ros:jazzy-ros-base

# ROS-only tests. Does not install Isaac Sim.
WORKDIR /platform
COPY . /platform
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3-pytest python3-yaml \
    && rm -rf /var/lib/apt/lists/*

CMD ["python3", "-m", "pytest", "tests/", "-q"]
