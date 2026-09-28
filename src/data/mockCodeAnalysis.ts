import { CodeReference, CodePath } from '@/types';

export const mockCodeReferences: CodeReference[] = [
  {
    id: 'ref-01',
    flagId: 'flag-02',
    flagName: 'LEGACY_OAUTH_V1_FALLBACK',
    repositoryId: 'repo-04',
    repositoryName: 'auth-identity-engine',
    filePath: 'src/main/java/com/acme/auth/OAuthFilter.java',
    lineNumber: 134,
    columnNumber: 12,
    codeSnippet: `if (FeatureFlagManager.isEnabled("LEGACY_OAUTH_V1_FALLBACK", context)) {
    logger.warn("Processing incoming request using deprecated OAuth 1.0a protocol.");
    return handleOAuth1Request(request, response);
} else {
    return handleStandardOAuth2(request, response);
}`,
    referenceType: 'check',
    isEnclosingControlFlow: true,
    astNodeType: 'IfStatement',
  },
  {
    id: 'ref-02',
    flagId: 'flag-04',
    flagName: 'DEPRECATED_STRIPE_WEBHOOK',
    repositoryId: 'repo-01',
    repositoryName: 'core-checkout-service',
    filePath: 'src/services/webhookHandler.ts',
    lineNumber: 142,
    columnNumber: 8,
    codeSnippet: `export async function processPaymentWebhook(payload: WebhookPayload) {
  if (flagClient.evaluate('DEPRECATED_STRIPE_WEBHOOK', { tenantId: payload.tenant })) {
    // DEAD CODE: legacy webhook format no longer emitted by provider
    return handleLegacyStripePayload(payload);
  }
  return handleModernStripeV3Event(payload);
}`,
    referenceType: 'check',
    isEnclosingControlFlow: true,
    astNodeType: 'IfStatement',
  },
  {
    id: 'ref-03',
    flagId: 'flag-07',
    flagName: 'OLD_CHECKOUT_UPSELL_CARD',
    repositoryId: 'repo-01',
    repositoryName: 'core-checkout-service',
    filePath: 'src/components/CheckoutSummary.tsx',
    lineNumber: 89,
    columnNumber: 15,
    codeSnippet: `<div className="checkout-sidebar">
  {isFeatureEnabled('OLD_CHECKOUT_UPSELL_CARD') ? (
    <StaticUpsellBanner items={HARDCODED_ITEMS} />
  ) : (
    <DynamicRecommendationWidget userId={user.id} />
  )}
</div>`,
    referenceType: 'check',
    isEnclosingControlFlow: true,
    astNodeType: 'ConditionalExpression',
  },
  {
    id: 'ref-04',
    flagId: 'flag-05',
    flagName: 'COOKIE_CONSENT_MODAL_2023',
    repositoryId: 'repo-03',
    repositoryName: 'customer-portal-web',
    filePath: 'src/features/compliance/ConsentBanner.tsx',
    lineNumber: 48,
    columnNumber: 5,
    codeSnippet: `const showLegacyConsent = flags['COOKIE_CONSENT_MODAL_2023'] ?? false;
if (showLegacyConsent) {
  renderLegacyCookieModal();
}`,
    referenceType: 'cleanup-candidate',
    isEnclosingControlFlow: true,
    astNodeType: 'VariableDeclaration',
  },
];

export const mockCodePaths: CodePath[] = [
  {
    id: 'path-01',
    flagId: 'flag-04',
    filePath: 'src/services/webhookHandler.ts',
    branchCondition: 'DEPRECATED_STRIPE_WEBHOOK == true',
    reachableState: false,
    deadCodeLines: [143, 144, 145, 146],
    deadCodeSnippet: `// Unreachable branch to be deleted by Piranha
return handleLegacyStripePayload(payload);`,
    complexityReductionScore: 18,
  },
  {
    id: 'path-02',
    flagId: 'flag-07',
    filePath: 'src/components/CheckoutSummary.tsx',
    branchCondition: 'OLD_CHECKOUT_UPSELL_CARD == true',
    reachableState: false,
    deadCodeLines: [90, 91],
    deadCodeSnippet: `<StaticUpsellBanner items={HARDCODED_ITEMS} />`,
    complexityReductionScore: 12,
  },
  {
    id: 'path-03',
    flagId: 'flag-02',
    filePath: 'src/main/java/com/acme/auth/OAuthFilter.java',
    branchCondition: 'LEGACY_OAUTH_V1_FALLBACK == true',
    reachableState: false,
    deadCodeLines: [135, 136, 137],
    deadCodeSnippet: `logger.warn("Processing incoming request using deprecated OAuth 1.0a protocol.");
return handleOAuth1Request(request, response);`,
    complexityReductionScore: 25,
  },
];
