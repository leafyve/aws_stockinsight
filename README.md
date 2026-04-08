# aws_stockinsight
Cloud-hosted Flask web app on AWS EC2 + S3 for stock data visualization (yfinance, Plotly)

# StockInsight
**StockInsight** is a lightweight web application that provides real-time stock data and basic technical indicators for major equities. Built with **Flask** on the backend and deployed on **AWS EC2**, it fetches live market data via the Yahoo Finance API (yfinance) and displays interactive charts using **Plotly**. Static assets (CSS, JavaScript) are hosted on **AWS S3** for faster content delivery. The app is containerized with **Gunicorn** and proxied through **Nginx**, with **systemd** ensuring automatic restart on failure. IAM roles enforce least-privilege access, and security groups restrict inbound traffic to SSH (admin) and HTTP (public). Perfect for learning cloud deployment patterns while exploring market trends.

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
