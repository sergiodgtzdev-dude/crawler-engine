using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.AspNetCore.Localization;
using Microsoft.AspNetCore.Mvc;
using SearchEngineAPI.DTO;
using StackExchange.Redis;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Xml.Linq;



var builder = WebApplication.CreateBuilder(args);

//Extracting Auth_token from dotnet secrets
var secretAuthKey = builder.Configuration["AdminSettings:SecretKey"];

//Extracting connection string from appsettings.json or environment variable
var redisConnectionString = builder.Configuration.GetConnectionString("Redis") ?? "localhost:6379";

// Add services to the container.

builder.Services.AddControllers();
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

//Parsing the connection string and configuring Redis options
ConfigurationOptions config = ConfigurationOptions.Parse(redisConnectionString);
config.AbortOnConnectFail = false;
config.ConnectRetry = 5;
config.ConnectTimeout = 5000;
config.SyncTimeout = 5000;

ConfigurationOptions adminConfig = config.Clone();
adminConfig.AllowAdmin = true;

//Using keyed Connections
//Connection for normal queries such as GET
builder.Services.AddSingleton<IConnectionMultiplexer>(sp => 
ConnectionMultiplexer.Connect(config));

//Connection for actions that require admin privieleges
builder.Services.AddKeyedSingleton<IConnectionMultiplexer>("admin-redis", (sp, key) =>
    ConnectionMultiplexer.Connect(adminConfig));

var app = builder.Build();


// Test endpoint for Redis
app.MapGet("/test-redis", (IConnectionMultiplexer redis) =>
{
    try
    {
        var db = redis.GetDatabase(0);
        // PING the database for latency
        var latency = db.Ping();

        RedisValue redisData = db.StringGet("crawl:laptop_origins");


        // Verify if the key exists in Redis
        if (!redisData.HasValue)
        {
            return Results.NotFound(new
            {
                status = "Conectado a Redis, pero la clave 'laptop_origins' no existe.",
                latencyMs = latency.TotalMilliseconds
            });
        } 
        else
        {
            // Convert redis Data to a string for deserialization
            string redisDataString = redisData.ToString().Trim();
            var options = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
                PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
            };

            List<CrawlResponse>? jsonParsedList = JsonSerializer.Deserialize<List<CrawlResponse>>(redisDataString, options);
            return Results.Ok(new
            {
                status = "¡Conectado exitosamente a Redis!",
                message = "La clave 'laptop_origins' existe en la base de datos, mensaje cargado con éxito",
                latencyMs = latency.TotalMilliseconds,
                testResult = jsonParsedList[1]
            });
        }

        
    }
    catch (Exception ex)
    {
        return Results.Problem($"Error de conexión: {ex.Message}");
    }
});

app.MapGet("api/search", async (string q, IConnectionMultiplexer redis) =>
{
    // Implementation for the search endpoint
    if (string.IsNullOrWhiteSpace(q)){
        return Results.BadRequest(new { error = "A search term is required" });

    }
    else
    {
        string redisKey = $"crawl:{q.Trim().ToLower().Replace(" ", "_")}";
        var db = redis.GetDatabase(0);
        var latency = db.Ping();
        
        //Searching for search term

        RedisValue redisData = db.StringGet($"{redisKey}");
        if (!redisData.HasValue)
        {
            //No value found, pushing the term for search to a redis queue for python backend to crawl

            await db.ListLeftPushAsync("queue:crawling", q);
            return Results.Accepted(uri: $"api/search?q={q}" , value: new
            {
                status = "Pending",
                message = $"Searching for term from the python backend {redisKey}",
                queueKey = "queue:crawling"
            });

        }
        else
        {
            //Deserializing the JSON Object from Redis
            string redisDataString = redisData.ToString().Trim();
            var options = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
                PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
            };


            List<CrawlResponse>? jsonParsedList = JsonSerializer.Deserialize<List<CrawlResponse>>(redisDataString, options);

            //separtes query string by keyword
            string[] searchWords = q.Split(' ', StringSplitOptions.RemoveEmptyEntries);

            List<CrawlResponse> filteredResults = jsonParsedList
            .Where(p => searchWords.Any(word =>
                (p.Metadata?.Title?.Contains(word, StringComparison.OrdinalIgnoreCase) ?? false) ||
                (p.Content?.CleanText?.Contains(word, StringComparison.OrdinalIgnoreCase) ?? false) ||
                (p.Metadata?.Description?.Contains(word, StringComparison.OrdinalIgnoreCase) ?? false)
            ))
            .ToList();

            foreach (CrawlResponse p in filteredResults)
            {
                Console.Write($"Title: {p.Metadata.Title}, Desc: {p.Metadata.Description}\n");
            }

            return Results.Ok(new
            {
                status = "Connected to Redis",
                message = $"Found information for term {redisKey} in redis cache",
                latency = latency,
                totalFilteredResults = filteredResults.Count(),
                totalResults = jsonParsedList.Count(),
                sampleResult = jsonParsedList.FirstOrDefault()

            });
        }
    }
});

app.MapDelete("api/admin/flush", (HttpRequest request, [FromKeyedServices("admin-redis")]IConnectionMultiplexer redis) =>
{
    try
    {
        string? authHeader = request.Headers.Authorization;

        if (string.IsNullOrEmpty(authHeader) || !authHeader.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
        {
            return Results.Unauthorized(); // HTTP 401
        }

        authHeader = authHeader.Substring("Bearer ".Length).Trim();

        if (string.IsNullOrEmpty(secretAuthKey) && !authHeader.Equals(secretAuthKey.ToString(), StringComparison.Ordinal))
        {
            return Results.Unauthorized();
        }
        else
        {
            var endpoints = redis.GetEndPoints();
            var server = redis.GetServer(endpoints.First());
            server.FlushDatabase(0); // Flush database 0
            return Results.Ok(new { message = "Redis Cache flushed successfully" });
        }

    }
    catch(Exception e)
    {
        return Results.BadRequest();
    }
    
    
});

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseHttpsRedirection();

app.UseAuthorization();

app.MapControllers();

app.Run();
