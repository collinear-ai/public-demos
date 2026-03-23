FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    xz-utils \
    build-essential \
    python3 \
    python3-pip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Zig 0.13.0 (compatible with ZLS at this commit)
RUN wget -q https://ziglang.org/download/0.13.0/zig-linux-x86_64-0.13.0.tar.xz \
    && tar -xf zig-linux-x86_64-0.13.0.tar.xz \
    && mv zig-linux-x86_64-0.13.0 /usr/local/zig \
    && ln -s /usr/local/zig/zig /usr/local/bin/zig \
    && rm zig-linux-x86_64-0.13.0.tar.xz

RUN zig version

# Clone the ZLS repository and checkout base commit
RUN git clone https://github.com/zigtools/zls.git /testbed
WORKDIR /testbed
RUN git checkout b2e89dfe

# Create required Harbor directories
RUN mkdir -p /logs/verifier /logs/agent /solution /tests

WORKDIR /testbed
