# Lazy_Bird Claude Agent Docker Image
# =====================================
# Provides a secure, isolated environment for running Claude Code agents
# Includes all necessary dependencies for multi-framework development

FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install base dependencies
RUN apt-get update && apt-get install -y \
    # Core utilities
    curl \
    wget \
    git \
    gnupg \
    ca-certificates \
    software-properties-common \
    # Python
    python3 \
    python3-pip \
    python3-venv \
    # Node.js dependencies
    nodejs \
    npm \
    # Build tools
    build-essential \
    cmake \
    pkg-config \
    # Godot dependencies
    libxcursor1 \
    libxinerama1 \
    libxrandr2 \
    libxi6 \
    libglu1-mesa \
    libgl1 \
    libasound2 \
    libpulse0 \
    # Git worktree support
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (optional, for Rust/Bevy projects)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Go (optional, for Go projects)
RUN wget -q https://go.dev/dl/go1.21.5.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz && \
    rm go1.21.5.linux-amd64.tar.gz
ENV PATH="/usr/local/go/bin:${PATH}"

# Install common Python packages
RUN pip3 install --no-cache-dir \
    pytest \
    pytest-cov \
    black \
    flake8 \
    requests \
    pyyaml

# Install Godot (version 4.2 - adjust as needed)
ARG GODOT_VERSION=4.2.1
RUN wget -q https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}-stable/Godot_v${GODOT_VERSION}-stable_linux.x86_64.zip -O /tmp/godot.zip && \
    unzip -q /tmp/godot.zip -d /usr/local/bin/ && \
    mv /usr/local/bin/Godot_v${GODOT_VERSION}-stable_linux.x86_64 /usr/local/bin/godot && \
    chmod +x /usr/local/bin/godot && \
    rm /tmp/godot.zip

# Install Claude Code CLI
# Note: This is a placeholder - actual installation depends on Claude Code distribution
# Users should replace this with the actual Claude Code installation method
# RUN curl -L https://claude.ai/download/cli | bash

# Create workspace directory
RUN mkdir -p /workspace
WORKDIR /workspace

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash agent && \
    chown -R agent:agent /workspace

# Switch to non-root user
USER agent

# Set up environment
ENV PYTHONUNBUFFERED=1
ENV GIT_TERMINAL_PROMPT=0

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -x godot > /dev/null || exit 0

# Default command (override at runtime)
CMD ["/bin/bash"]

# Labels
LABEL maintainer="Lazy_Bird Project"
LABEL description="Secure environment for Claude Code agents with multi-framework support"
LABEL version="1.0"
