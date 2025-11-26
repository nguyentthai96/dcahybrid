
Next.js (App Router) 
npx create-next-app@latest

React Router (v7) 
npx create-react-router@latest

Create with template
npm create vite@latest my-app -- --template react-ts

Adding TypeScript to an existing React project 
npm install —save-dev @types/react @types/react-dom



yarn global add react-devtools

Install React Compiler as a devDependency:
npm install -D babel-plugin-react-compiler@latest
or
yarn add -D babel-plugin-react-compiler@latest
or
pnpm install -D babel-plugin-react-compiler@latest



Instructions to setup and run:

Ubuntu add user into "input" group
sudo usermod -aG input $USER
newgrp input

sudo apt install python3 python3-pip python3-venv python3-full -y
python3 -m venv .venv
source .venv/bin/activate
python3 mouse_python.py
install library
pip install -U pip setuptools wheel pyinstaller
pip freeze > requirements.txt

pyinstaller --onefile --hidden-import=evdev --hidden-import=sklearn --hidden-import=joblib





npx hardhat node
https://app.tryethernal.com/blocks

# Khởi tạo blockchain local và lưu DB
ganache --db /home/nguyentthai96/Desktop/dcahybrid/hybridsmartcontract/mychain --chain.chainId 31337 --accounts 10
