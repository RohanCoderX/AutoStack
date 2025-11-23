#!/bin/bash
# AutoStack EC2 User Data Script

# Update system
yum update -y

# Install Docker
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create app directory
mkdir -p /opt/autostack
cd /opt/autostack

# Create docker-compose file
echo "${docker_compose}" | base64 -d > docker-compose.yml

# Create environment file
echo "${env_file}" | base64 -d > .env

# Create data directory for SQLite
mkdir -p data
chmod 777 data

# Clone AutoStack repository
yum install -y git
git clone https://github.com/RohanCoderX/AutoStack.git /tmp/autostack
cp -r /tmp/autostack/services /opt/autostack/

# Start services
docker-compose up -d

# Create systemd service for auto-start
cat > /etc/systemd/system/autostack.service << EOF
[Unit]
Description=AutoStack Services
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/autostack
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl enable autostack.service

# Install CloudWatch agent for monitoring
yum install -y amazon-cloudwatch-agent

# Create simple health check
cat > /opt/autostack/health-check.sh << 'EOF'
#!/bin/bash
curl -f http://localhost:3000/health || exit 1
EOF
chmod +x /opt/autostack/health-check.sh

# Install cronie for cron jobs
yum install -y cronie
systemctl start crond
systemctl enable crond

# Add cron job for health monitoring
echo "*/5 * * * * /opt/autostack/health-check.sh" | crontab -

echo "AutoStack installation completed" > /var/log/autostack-install.log