import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/assigned_forms/forms_screen.dart';
import '../features/authentication/login_screen.dart';
import '../features/dashboard/dashboard_screen.dart';
import '../features/dynamic_form_renderer/form_screen.dart';
import '../features/submissions/history_screen.dart';
import 'providers.dart';
import 'theme.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<int>(0);
  ref.listen(authProvider.select((a) => a.status), (_, __) => refresh.value++);
  ref.onDispose(refresh.dispose);
  return GoRouter(
    initialLocation: '/',
    refreshListenable: refresh,
    redirect: (context, state) {
      final status = ref.read(authProvider).status;
      final loggingIn = state.matchedLocation == '/login';
      if (status == AuthStatus.unknown) return null;
      if (status == AuthStatus.signedOut) return loggingIn ? null : '/login';
      return loggingIn ? '/' : null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      ShellRoute(
        builder: (context, state, child) => _Shell(child: child),
        routes: [
          GoRoute(path: '/', builder: (_, __) => const DashboardScreen()),
          GoRoute(path: '/forms', builder: (_, __) => const FormsScreen()),
          GoRoute(path: '/history', builder: (_, __) => const HistoryScreen()),
        ],
      ),
      GoRoute(path: '/form/:id', builder: (_, s) => FormScreen(draftId: s.pathParameters['id']!)),
      GoRoute(path: '/submission/:id', builder: (_, s) => SubmissionDetailScreen(localId: s.pathParameters['id']!)),
    ],
  );
});

class _Shell extends ConsumerWidget {
  const _Shell({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loc = GoRouterState.of(context).matchedLocation;
    final idx = loc.startsWith('/forms') ? 1 : loc.startsWith('/history') ? 2 : 0;
    final pending = (ref.watch(submissionsProvider).valueOrNull ?? const []).where((s) => s.state != 'accepted').length;
    return Scaffold(
      body: child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: idx,
        onDestinationSelected: (i) => context.go(['/', '/forms', '/history'][i]),
        destinations: [
          const NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home_rounded), label: 'Home'),
          const NavigationDestination(icon: Icon(Icons.assignment_outlined), selectedIcon: Icon(Icons.assignment_rounded), label: 'Forms'),
          NavigationDestination(
            icon: Badge(isLabelVisible: pending > 0, label: Text('$pending'), backgroundColor: Brand.gold500, textColor: Brand.navy900, child: const Icon(Icons.history_rounded)),
            selectedIcon: Badge(isLabelVisible: pending > 0, label: Text('$pending'), backgroundColor: Brand.gold500, textColor: Brand.navy900, child: const Icon(Icons.history_rounded)),
            label: 'History',
          ),
        ],
      ),
    );
  }
}

class FieldSyncApp extends ConsumerStatefulWidget {
  const FieldSyncApp({super.key});
  @override
  ConsumerState<FieldSyncApp> createState() => _FieldSyncAppState();
}

class _FieldSyncAppState extends ConsumerState<FieldSyncApp> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    Future.microtask(() => ref.read(authProvider.notifier).restore()); // triggers a sync on start
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) ref.read(syncProvider.notifier).trigger('resume');
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'FieldSync',
      debugShowCheckedModeBanner: false, // no red DEBUG ribbon over the app's corner
      theme: buildTheme(),
      routerConfig: ref.watch(routerProvider),
    );
  }
}
