# Config-Stash Development Container
FROM mcr.microsoft.com/devcontainers/python:3.12

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    # Build tools
    build-essential \
    pkg-config \
    # Network tools
    curl \
    wget \
    net-tools \
    dnsutils \
    iputils-ping \
    # Database clients (for testing)
    postgresql-client \
    sqlite3 \
    # Security tools
    gnupg \
    ca-certificates \
    # Shell enhancement
    zsh \
    vim \
    nano \
    # Other utilities
    jq \
    tree \
    htop \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Install Python development tools globally
RUN pip install --no-cache-dir --upgrade \
    pip \
    setuptools \
    wheel \
    hatchling

# Install HashiCorp Vault CLI
ARG VAULT_VERSION=1.15.4
RUN wget https://releases.hashicorp.com/vault/${VAULT_VERSION}/vault_${VAULT_VERSION}_linux_amd64.zip \
    && unzip vault_${VAULT_VERSION}_linux_amd64.zip \
    && mv vault /usr/local/bin/ \
    && chmod +x /usr/local/bin/vault \
    && rm vault_${VAULT_VERSION}_linux_amd64.zip

# Install AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip ./aws

# Install Azure CLI
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Install Google Cloud SDK
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
    | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && apt-get update \
    && apt-get install -y google-cloud-sdk \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Create workspace directory
RUN mkdir -p /workspace && chown vscode:vscode /workspace

# Switch to vscode user for remaining setup
USER vscode

# Setup ZSH with Oh My Zsh (if not already done by feature)
RUN if [ ! -d "$HOME/.oh-my-zsh" ]; then \
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended; \
    fi

# Configure ZSH
RUN echo 'export ZSH="$HOME/.oh-my-zsh"' >> ~/.zshrc \
    && echo 'ZSH_THEME="robbyrussell"' >> ~/.zshrc \
    && echo 'plugins=(git python docker kubectl aws)' >> ~/.zshrc \
    && echo 'source $ZSH/oh-my-zsh.sh' >> ~/.zshrc \
    && echo '' >> ~/.zshrc \
    && echo '# Config-Stash aliases' >> ~/.zshrc \
    && echo 'alias pytest="python -m pytest"' >> ~/.zshrc \
    && echo 'alias test="python -m pytest tests/"' >> ~/.zshrc \
    && echo 'alias test-cov="python -m pytest tests/ --cov=src/config_stash --cov-report=html"' >> ~/.zshrc \
    && echo 'alias lint="ruff check ."' >> ~/.zshrc \
    && echo 'alias format="black . && isort ."' >> ~/.zshrc \
    && echo 'alias typecheck="mypy src/config_stash"' >> ~/.zshrc \
    && echo 'alias check-all="make check"' >> ~/.zshrc \
    && echo 'alias vault-dev="vault server -dev -dev-root-token-id=dev-token-12345"' >> ~/.zshrc

# Setup git aliases
RUN git config --global alias.st status \
    && git config --global alias.co checkout \
    && git config --global alias.br branch \
    && git config --global alias.ci commit \
    && git config --global alias.lg "log --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit"

# Set default shell to zsh
ENV SHELL=/bin/zsh

# Working directory
WORKDIR /workspace

# Healthcheck (optional, good practice)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python --version || exit 1
