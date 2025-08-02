import { Test, TestingModule } from "@nestjs/testing";
import { DocumentService } from "./document.service";
import { AzureOpenAIService } from "./azure-openai.service";
import { CosmosDbService } from "./cosmosdb.service";

describe("DocumentService", () => {
  let service: DocumentService;
  let cosmosDbService: CosmosDbService;
  let azureOpenAIService: AzureOpenAIService;

  beforeEach(async () => {
    const mockCosmosDbService = {
      createItem: vi.fn(),
      getItem: vi.fn(),
      updateItem: vi.fn(),
      deleteItem: vi.fn(),
      queryItems: vi.fn(),
    };

    const mockAzureOpenAIService = {
      answerQuestionWithContext: vi.fn(),
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        DocumentService,
        {
          provide: CosmosDbService,
          useValue: mockCosmosDbService,
        },
        {
          provide: AzureOpenAIService,
          useValue: mockAzureOpenAIService,
        },
      ],
    }).compile();

    service = module.get<DocumentService>(DocumentService);
    cosmosDbService = module.get<CosmosDbService>(CosmosDbService);
    azureOpenAIService = module.get<AzureOpenAIService>(AzureOpenAIService);
  });

  it("should be defined", () => {
    expect(service).toBeDefined();
  });

  it("should create a document with Cosmos DB integration", async () => {
    const mockFile = {
      originalname: "test.pdf",
      buffer: Buffer.from("mock pdf content"),
      mimetype: "application/pdf",
      size: 1024,
    };

    const mockCreateItem = vi.fn().mockResolvedValue({
      resource: { id: "test-id", filename: "test.pdf" },
    });
    cosmosDbService.createItem = mockCreateItem;

    // Mock pdf-parse
    vi.mock("pdf-parse", () => ({
      default: vi.fn().mockResolvedValue({
        text: "This is a test document content.",
        numpages: 1,
      }),
    }));

    const result = await service.processDocument(mockFile, "user123");

    expect(result).toBeDefined();
    expect(result.filename).toBe("test.pdf");
    expect(result.partitionKey).toBe("user123");
    expect(result.userId).toBe("user123");
    expect(cosmosDbService.createItem).toHaveBeenCalled();
  });

  it("should retrieve documents for a user", async () => {
    const mockDocuments = [
      {
        id: "doc1",
        filename: "test1.pdf",
        partitionKey: "user123",
        chunks: [],
        uploadedAt: new Date(),
      },
    ];

    const mockQueryItems = vi.fn().mockResolvedValue(mockDocuments);
    cosmosDbService.queryItems = mockQueryItems;

    const result = await service.getAllDocuments("user123");

    expect(result).toEqual(mockDocuments);
    expect(cosmosDbService.queryItems).toHaveBeenCalledWith({
      query: "SELECT * FROM c WHERE c.partitionKey = @partitionKey",
      parameters: [
        {
          name: "@partitionKey",
          value: "user123",
        },
      ],
    });
  });

  it("should delete a document", async () => {
    const mockDeleteItem = vi.fn().mockResolvedValue({});
    cosmosDbService.deleteItem = mockDeleteItem;

    const result = await service.deleteDocument("doc1", "user123");

    expect(result).toBe(true);
    expect(cosmosDbService.deleteItem).toHaveBeenCalledWith("doc1", "user123");
  });
});
