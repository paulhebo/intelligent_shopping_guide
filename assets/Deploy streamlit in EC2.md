# Deploy streamlit in EC2

### 1.Create EC2 instance

Network settings choose "Allow HTTP traffic from the internet"

### 2.Connect to EC2, install the following dependencies:

1. sudo yum update
2. sudo yum install nginx
3. sudo yum install tmux -y
4. sudo yum install python3-pip
5. pip3 install streamlit==1.27.2
6. pip3 install langchain==0.0.310 (No need to deploy in the china region)
7. pip3 install boto3 (No need to deploy in the china region)


### 3.upload template_ui.py file to EC2

Filling the parameters：

* chat_bot_invoke_url
* product_search_invoke_url
* ads_invoke_url
* index
* apiKey

### 4.Create nginx profiles

1. cd /etc/nginx/conf.d
2. sudo touch streamlit.conf
3. sudo chmod 777 streamlit.conf
4. vi streamlit.conf

enter the template:

upstream ws-backend {
        server xxx.xxx.xxx.xxx:8501;
}

server {
    listen 80;
    server_name xxx.xxx.xxx.xxx;

    location / {
            
    proxy_pass http://ws-backend;

    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header Host $http_host;
      proxy_redirect off;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
    }
  }

Change the xxx.xxx.xxx.xxx to the EC2 private IP.


5. start nginx：sudo systemctl start nginx.service

### 5.Run streamlit ui stript

1. cd /home/ec2-user/
2. mkdir shopping_guide
3. cd shooping_guide
4. download the template_ui.py (can download from s3, or create a new file)
5. tmux
6. streamlit run template_ui.py

### 6.Open streamlit page

Enter the url in the webpage：http://<EC2 public IP>
