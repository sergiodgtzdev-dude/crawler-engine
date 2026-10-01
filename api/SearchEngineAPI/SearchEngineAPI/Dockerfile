# Stage 1: Compilation
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

# Copy csproj and dependencies
COPY ["SearchEngineAPI.csproj", "./"]
RUN dotnet restore "SearchEngineAPI.csproj"

# Copy the rest of the code and compile
COPY . .
RUN dotnet publish "SearchEngineAPI.csproj" -c Release -o /app/publish /p:UseAppHost=false

# Stage 2: Final image for execution
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS final
WORKDIR /app
COPY --from=build /app/publish .

EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080

ENTRYPOINT ["dotnet", "SearchEngineAPI.dll"]