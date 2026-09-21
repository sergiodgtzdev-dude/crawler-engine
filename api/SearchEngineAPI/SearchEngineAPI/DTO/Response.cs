using System.Text.Json.Serialization;
namespace SearchEngineAPI.DTO
{
    public record CrawlResponse(
        [property: JsonPropertyName("url")] string Url,
        [property: JsonPropertyName("status_code")] int StatusCode,
        [property: JsonPropertyName("crawled_at")] string CrawledAt,
        [property: JsonPropertyName("metadata")] UrlMetadata Metadata,
        [property: JsonPropertyName("content")] CrawlContent Content
    );

    public record UrlMetadata(
        [property: JsonPropertyName("title")] string Title,
        [property: JsonPropertyName("description")] string Description,
        [property: JsonPropertyName("language")] string Language
    );

    public record CrawlContent(
        [property: JsonPropertyName("h1")] List<string> H1,
        [property: JsonPropertyName("h2")] List<string> H2,
        [property: JsonPropertyName("clean_text")] string CleanText
    );
}
