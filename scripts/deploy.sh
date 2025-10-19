npm install --prefix src/kohaku-hub-admin
npm install --prefix src/kohaku-hub-ui
npm run build --prefix src/kohaku-hub-admin
npm run build --prefix src/kohaku-hub-ui
docker compose up -d --build