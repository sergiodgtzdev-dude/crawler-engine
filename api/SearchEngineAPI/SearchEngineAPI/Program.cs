using SearchEngineAPI.DTO;
using StackExchange.Redis;
using System.Text.Json;


var builder = WebApplication.CreateBuilder(args);

// Add services to the container.

builder.Services.AddControllers();
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

//Extracting connection string from appsettings.json or environment variable
var redisConnectionString = builder.Configuration.GetConnectionString("Redis") ?? "localhost:6379";

//Parsing the connection string and configuring Redis options
ConfigurationOptions config = ConfigurationOptions.Parse(redisConnectionString);
config.AbortOnConnectFail = false;
config.ConnectRetry = 5;
config.ConnectTimeout = 5000;
config.SyncTimeout = 5000;


builder.Services.AddSingleton<IConnectionMultiplexer>(sp => ConnectionMultiplexer.Connect(config));

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

            List<CrawlResponse>? jsonParsedList = JsonSerializer.Deserialize<List<CrawlResponse>>(redisDataString);
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

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseHttpsRedirection();

app.UseAuthorization();

app.MapControllers();

app.Run();
