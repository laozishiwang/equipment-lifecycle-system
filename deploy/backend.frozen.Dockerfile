FROM eclipse-temurin:17-jre
WORKDIR /app
COPY ruoyi-admin.jar /app/app.jar
ENTRYPOINT ["java","-jar","/app/app.jar"]
