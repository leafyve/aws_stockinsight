# StockInsight — Setup & Run Guide

## Prerequisites

- Python 3.9+
- pip

## Quick Start

## 🌐 Live Demo

The application is deployed on AWS Elastic Beanstalk (Singapore region):  
[http://stockinsight-env.eba-y6tqvmr9.ap-southeast-1.elasticbeanstalk.com](http://stockinsight-env.eba-y6tqvmr9.ap-southeast-1.elasticbeanstalk.com)

> ⚠️ The free tier instance may be stopped occasionally to manage costs. If the link doesn’t work, the instance is paused.

## ☁️ AWS Deployment Architecture

- **Compute**: AWS Elastic Beanstalk (EC2 t3.micro, Amazon Linux 2023)  
- **Static Assets**: Amazon S3 bucket with public-read policy  
- **Web Server**: Gunicorn + Nginx (reverse proxy) managed by Elastic Beanstalk  
- **Process Management**: systemd (auto‑restart)  
- **Infrastructure as Code**: EB CLI with `Procfile` and environment variables  

### Manual EC2 Deployment (Alternative)

The same application was also deployed manually on an EC2 instance with:
- Custom Nginx reverse proxy, Gunicorn, systemd service
- IAM role for S3 read access
- Security groups (SSH, HTTP, port 5000)

See the [`manual-ec2-deployment`](https://github.com/leafyve/stockinsight/tree/manual-ec2) branch for configuration files.

## 🛠️ Production Troubleshooting Learned

- Fixed `ModuleNotFoundError: No module named 'application'` by creating a correct `Procfile` (`web: gunicorn application:app`).  
- Resolved Gunicorn worker boot failures by manually editing systemd unit via SSH.  
- Debugged health check red status using `eb logs` and `web.stdout.log`.  
- Propagated environment variables (`STATIC_BASE`) through Elastic Beanstalk environment properties.
