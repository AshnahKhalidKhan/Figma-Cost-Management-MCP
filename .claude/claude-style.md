# Claude Style Guide

Modular style rules for the Microsoft 365 Billing MCP project.
Apply these rules to ALL generated or modified code files without exception.

---

## 1. Brace Style — Always Next Line (Allman Style)

Opening braces go on the **next line** for all blocks: functions, classes, interfaces,
if/else, loops, try/catch, switch, object literals in declarations, etc.

```typescript
// CORRECT
function getSubscriptionById(subscriptionId: string): Promise<Subscription>
{
    return subscriptionRepository.findById(subscriptionId);
}

class InvoiceService
{
    constructor(private readonly partnerCenterApiClient: PartnerCenterApiClient)
    {
    }

    async getInvoiceById(invoiceId: string): Promise<Invoice>
    {
        if (!invoiceId)
        {
            throw new Error("invoiceId must not be empty.");
        }
        return this.partnerCenterApiClient.fetchInvoice(invoiceId);
    }
}

// WRONG — do not do this
function getSubscriptionById(subscriptionId: string) {
    ...
}
```

---

## 2. Semicolons — Always Add Them

TypeScript makes semicolons optional, but this project **always uses them**. Every
statement ends with a semicolon.

```typescript
// CORRECT
const invoiceId: string = "INV-001";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

// WRONG
const invoiceId = "INV-001"
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js"
```

---

## 3. Naming Conventions — Verbose and Descriptive

Names must be self-explanatory. A reader should understand what a name refers to
without reading its implementation.

| Construct | Convention | Example |
|---|---|---|
| Classes | PascalCase, noun phrase | `PartnerCenterInvoiceService`, `MicrosoftGraphApiClient` |
| Interfaces | PascalCase, noun phrase (no `I` prefix) | `SubscriptionResource`, `InvoiceLineItem` |
| Type aliases | PascalCase | `BillingCycleType`, `SubscriptionStatus` |
| Functions / methods | camelCase, verb phrase | `getSubscriptionById`, `assignLicenseToUser`, `listInvoicesForBillingPeriod` |
| Getters | `get` + PascalCase property name | `getWindowWidth`, `getTenantId`, `getBillingProfileAddress` |
| Setters | `set` + PascalCase property name | `setWindowWidth`, `setTenantId` |
| Boolean variables | `is`, `has`, `can`, `should` prefix | `isTrialSubscription`, `hasActiveLicense`, `canTransitionToAnnual` |
| Constants | UPPER_SNAKE_CASE | `PARTNER_CENTER_BASE_URL`, `GRAPH_API_BASE_URL`, `MAX_RETRY_ATTEMPTS` |
| Private class fields | camelCase with no underscore prefix | `tenantId` (NOT `_tenantId`) |
| Enum members | PascalCase | `SubscriptionStatus.Active`, `BillingCycle.Monthly` |
| File names | PascalCase matching the primary export | `InvoiceService.ts`, `SubscribedSkuTools.ts` |
| Test files | `<SourceFileName>.test.ts` | `InvoiceService.test.ts` |

**Avoid abbreviations.** Never shorten unless the abbreviation is universally known
(e.g., `id`, `url`, `http`, `api`).

```typescript
// CORRECT
const subscriptionRenewalDate: Date = new Date(subscription.nextLifecycleDateTime);
const totalConsumedLicenseUnits: number = subscribedSku.consumedUnits;

// WRONG — too terse
const renewDate = new Date(sub.nextLifecycle);
const consumed = sku.consumed;
```

---

## 4. TypeScript — Strict Mode, No `any`

- `tsconfig.json` must have `"strict": true`.
- Never use `any`. Use `unknown` when the type is truly unknown, then narrow with guards.
- All function parameters and return types must be explicitly annotated.
- Use `readonly` on class properties that should not be reassigned after construction.

```typescript
// CORRECT
async function fetchOrganizationBillingInfo(tenantId: string): Promise<OrganizationBillingInfo>
{
    const response: unknown = await graphApiClient.get(`/organization/${tenantId}`);
    return validateOrganizationBillingInfoResponse(response);
}

// WRONG
async function fetchOrgBilling(id: any): Promise<any>
{
    return await client.get(`/organization/${id}`);
}
```

---

## 5. Imports — Explicit, Grouped, Sorted

Order: (1) Node built-ins, (2) third-party packages, (3) internal project modules.
Separate each group with a blank line. Use named imports; avoid `import *`.

```typescript
import path from "path";

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import axios, { AxiosInstance } from "axios";
import { ConfidentialClientApplication } from "@azure/msal-node";

import { InvoiceService } from "../services/InvoiceService.js";
import { McpErrorHandler } from "../errors/McpErrorHandler.js";
import { Invoice, InvoiceLineItem } from "../models/Invoice.js";
```

---

## 6. Error Handling — Always Explicit

- Never catch and silently swallow errors.
- Catch at the tool layer; map to MCP error format via `McpErrorHandler`.
- Log errors with enough context to reproduce the failure (request ID, endpoint, status code).
- Never log secrets or credential values.

```typescript
try
{
    const invoice: Invoice = await invoiceService.getInvoiceById(invoiceId);
    return buildSuccessToolResult(invoice);
}
catch (error: unknown)
{
    return McpErrorHandler.buildErrorToolResult(error, { invoiceId });
}
```

---

## 7. Async/Await — Always Use Over Raw Promises

Prefer `async/await` everywhere. Only use `.then()/.catch()` chains for Promise
combinators (`Promise.all`, `Promise.allSettled`).

---

## 8. Comments — Only Where Logic Is Non-Obvious

Do not add JSDoc boilerplate to every function. Add a comment only when the code
does something that cannot be understood by reading it (e.g., a non-obvious API
quirk, a business rule, a workaround for a known API bug).

```typescript
// Partner Center returns HTTP 202 Accepted (not 200) for async subscription updates.
// We must poll the operation URL in the Location header to get the final result.
if (response.status === 202)
{
    return await pollAsyncOperation(response.headers["location"]);
}
```
