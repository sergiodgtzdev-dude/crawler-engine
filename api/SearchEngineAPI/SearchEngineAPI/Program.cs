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

//TODO : Implementar un endpoint para verificar la conexión a Redis y la existencia de la clave "laptop_origins" en la base de datos.
//Este endpoint debería devolver un mensaje indicando si la conexión fue exitosa y si la clave existe, junto con la latencia de la conexión.


// Endpoint temporal para verificar la conexión a Redis
app.MapGet("/test-redis", (IConnectionMultiplexer redis) =>
{
    try
    {
        var db = redis.GetDatabase(0);
        // Envía un comando PING a Redis y mide la latencia
        var latency = db.Ping();

        RedisValue redisData = db.StringGet("crawl:laptop_origins");

        // 2. Verificar si la clave realmente existe en la base de datos
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
            var jsonParsed = JsonDocument.Parse(redisData.ToString());
            return Results.Ok(new
            {
                status = "¡Conectado exitosamente a Redis!",
                latencyMs = latency.TotalMilliseconds,
                testResutls = jsonParsed.RootElement
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
