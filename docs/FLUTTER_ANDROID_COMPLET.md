# Makèt Peyizan — Guide Flutter Android Complet
> Intégralité des écrans web traduits en Dart/Flutter, avec les appels API vers `https://maketpeyizan.ht`

---

## Sommaire

1. [Configuration du projet](#1-configuration-du-projet)
2. [Constantes et configuration](#2-constantes-et-configuration)
3. [Modèles Dart](#3-modèles-dart)
4. [Service API (Dio + JWT)](#4-service-api)
5. [Authentification — Login](#5-login)
6. [Authentification — Inscription](#6-inscription)
7. [Catalogue public — Liste produits](#7-catalogue-liste)
8. [Catalogue public — Détail produit](#8-catalogue-détail)
9. [Panier](#9-panier)
10. [Checkout — Passer commande](#10-checkout)
11. [Dashboard Acheteur — Vue d'ensemble](#11-dashboard-acheteur)
12. [Acheteur — Mes commandes](#12-acheteur-commandes)
13. [Acheteur — Mes adresses](#13-acheteur-adresses)
14. [Acheteur — Mon profil](#14-acheteur-profil)
15. [Dashboard Producteur — Vue d'ensemble](#15-dashboard-producteur)
16. [Producteur — Commandes reçues](#16-producteur-commandes)
17. [Producteur — Mon catalogue](#17-producteur-catalogue)
18. [Producteur — Mes collectes](#18-producteur-collectes)
19. [Producteur — Mon profil](#19-producteur-profil)
20. [Producteur — En attente de validation](#20-producteur-en-attente)
21. [Sélecteur géographique (widget réutilisable)](#21-geo-selector)
22. [Navigation et routing](#22-navigation)

---

## 1. Configuration du projet

### `pubspec.yaml`

```yaml
name: maket_peyizan
description: Makèt Peyizan — Plateforme agricole haïtienne
version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter

  # HTTP & Auth
  dio: ^5.4.0
  dio_cookie_manager: ^3.1.1
  cookie_jar: ^4.0.8
  flutter_secure_storage: ^9.0.0

  # State management
  flutter_riverpod: ^2.5.1
  riverpod_annotation: ^2.3.5

  # Navigation
  go_router: ^13.2.0

  # Images
  cached_network_image: ^3.3.1
  image_picker: ^1.0.7

  # Push notifications
  firebase_core: ^2.27.0
  firebase_messaging: ^14.7.19

  # UI
  shimmer: ^3.0.0
  flutter_svg: ^2.0.10
  intl: ^0.19.0

  # Storage local
  shared_preferences: ^2.2.3

  # Autre
  equatable: ^2.0.5
  json_annotation: ^4.8.1

dev_dependencies:
  flutter_test:
    sdk: flutter
  build_runner: ^2.4.8
  json_serializable: ^6.7.1
  riverpod_generator: ^2.4.0
```

---

## 2. Constantes et configuration

### `lib/core/constants.dart`

```dart
class AppConstants {
  // Domaine de production
  static const String baseUrl = 'https://maketpeyizan.ht';
  static const String apiUrl  = '$baseUrl/api';

  // Clés de stockage sécurisé
  static const String keyAccess  = 'mp_access';
  static const String keyRefresh = 'mp_refresh';
  static const String keyUser    = 'mp_user';
  static const String keyFcm     = 'mp_fcm';

  // Pagination
  static const int pageSize = 20;

  // Rôles
  static const String roleAcheteur   = 'acheteur';
  static const String roleProducteur = 'producteur';
  static const String roleCollecteur = 'collecteur';
  static const String roleSuperadmin = 'superadmin';

  // Statuts producteur
  static const String statutEnAttente = 'en_attente';
  static const String statutActif     = 'actif';
  static const String statutSuspendu  = 'suspendu';
  static const String statutInactif   = 'inactif';

  // Couleurs métier (statuts)
  static const Map<String, int> statutColors = {
    'en_attente':    0xFFFF9800,
    'actif':         0xFF4CAF50,
    'suspendu':      0xFFF44336,
    'inactif':       0xFF9E9E9E,
    'confirmee':     0xFF2196F3,
    'en_preparation':0xFF9C27B0,
    'livree':        0xFF4CAF50,
    'annulee':       0xFFF44336,
    'paye':          0xFF4CAF50,
    'non_paye':      0xFFFF9800,
  };
}

/// Construit l'URL absolue d'une image renvoyée par l'API
String imageUrl(String? path) {
  if (path == null || path.isEmpty) return '';
  if (path.startsWith('http')) return path;
  return '${AppConstants.baseUrl}$path';
}
```

---

## 3. Modèles Dart

### `lib/models/user.dart`

```dart
import 'package:json_annotation/json_annotation.dart';
part 'user.g.dart';

@JsonSerializable()
class User {
  final int id;
  final String username;
  final String email;
  @JsonKey(name: 'first_name') final String firstName;
  @JsonKey(name: 'last_name')  final String lastName;
  @JsonKey(name: 'full_name')  final String? fullName;
  final String? telephone;
  final String? photo;
  @JsonKey(name: 'photo_url')  final String? photoUrl;
  final String role;
  @JsonKey(name: 'is_active')     final bool isActive;
  @JsonKey(name: 'is_superuser')  final bool isSuperuser;
  @JsonKey(name: 'is_staff')      final bool isStaff;
  @JsonKey(name: 'is_verified')   final bool isVerified;
  @JsonKey(name: 'profil_producteur_statut') final String? profilProducteurStatut;
  @JsonKey(name: 'created_at')    final String? createdAt;

  const User({
    required this.id,
    required this.username,
    required this.email,
    required this.firstName,
    required this.lastName,
    this.fullName,
    this.telephone,
    this.photo,
    this.photoUrl,
    required this.role,
    required this.isActive,
    required this.isSuperuser,
    required this.isStaff,
    required this.isVerified,
    this.profilProducteurStatut,
    this.createdAt,
  });

  bool get isAcheteur   => role == 'acheteur';
  bool get isProducteur => role == 'producteur';
  bool get isSuperAdmin => isSuperuser || isStaff || role == 'superadmin';
  bool get isProducteurActif => isProducteur && profilProducteurStatut == 'actif';
  String get displayName => fullName ?? '$firstName $lastName'.trim();

  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);
  Map<String, dynamic> toJson() => _$UserToJson(this);
}

@JsonSerializable()
class AuthResponse {
  final String access;
  final String refresh;
  final User user;

  const AuthResponse({
    required this.access,
    required this.refresh,
    required this.user,
  });

  factory AuthResponse.fromJson(Map<String, dynamic> json) {
    // Supporte { access, refresh, user } ou { data: { access, refresh, user } }
    final data = json.containsKey('data') ? json['data'] as Map<String, dynamic> : json;
    return AuthResponse(
      access:  data['access']  as String,
      refresh: data['refresh'] as String,
      user:    User.fromJson(data['user'] as Map<String, dynamic>),
    );
  }
}
```

### `lib/models/produit.dart`

```dart
import 'package:json_annotation/json_annotation.dart';
part 'produit.g.dart';

@JsonSerializable()
class Categorie {
  final int id;
  final String nom;
  final String slug;
  final String? icone;
  final String? image;

  const Categorie({required this.id, required this.nom, required this.slug, this.icone, this.image});
  factory Categorie.fromJson(Map<String, dynamic> json) => _$CategorieFromJson(json);
  Map<String, dynamic> toJson() => _$CategorieToJson(this);
}

@JsonSerializable()
class ProducteurMini {
  final int id;
  final String nom;
  final String? commune;
  final String? departement;
  @JsonKey(name: 'code_producteur') final String? codeProducteur;

  const ProducteurMini({required this.id, required this.nom, this.commune, this.departement, this.codeProducteur});
  factory ProducteurMini.fromJson(Map<String, dynamic> json) => _$ProducteurMiniFromJson(json);
  Map<String, dynamic> toJson() => _$ProducteurMiniToJson(this);
}

@JsonSerializable()
class Produit {
  final int id;
  final String nom;
  final String slug;
  final String? variete;
  final String? description;
  @JsonKey(name: 'prix_unitaire')       final String prixUnitaire;
  @JsonKey(name: 'prix_gros')           final String? prixGros;
  @JsonKey(name: 'unite_vente')         final String uniteVente;
  @JsonKey(name: 'unite_vente_label')   final String? uniteVenteLabel;
  @JsonKey(name: 'quantite_min_commande') final int quantiteMinCommande;
  @JsonKey(name: 'stock_disponible')    final int stockDisponible;
  @JsonKey(name: 'stock_reel')          final int? stockReel;
  @JsonKey(name: 'est_en_alerte')       final bool? estEnAlerte;
  final String statut;
  @JsonKey(name: 'is_active')           final bool isActive;
  @JsonKey(name: 'is_featured')         final bool isFeatured;
  @JsonKey(name: 'image_principale')    final String? imagePrincipale;
  final String? origine;
  final String? saison;
  final String? certifications;
  final Categorie? categorie;
  final ProducteurMini? producteur;
  final List<ImageProduit>? images;
  @JsonKey(name: 'created_at')          final String? createdAt;

  const Produit({
    required this.id,
    required this.nom,
    required this.slug,
    this.variete,
    this.description,
    required this.prixUnitaire,
    this.prixGros,
    required this.uniteVente,
    this.uniteVenteLabel,
    required this.quantiteMinCommande,
    required this.stockDisponible,
    this.stockReel,
    this.estEnAlerte,
    required this.statut,
    required this.isActive,
    required this.isFeatured,
    this.imagePrincipale,
    this.origine,
    this.saison,
    this.certifications,
    this.categorie,
    this.producteur,
    this.images,
    this.createdAt,
  });

  factory Produit.fromJson(Map<String, dynamic> json) => _$ProduitFromJson(json);
  Map<String, dynamic> toJson() => _$ProduitToJson(this);
}

@JsonSerializable()
class ImageProduit {
  final int id;
  final String image;
  final String? legende;
  final int ordre;

  const ImageProduit({required this.id, required this.image, this.legende, required this.ordre});
  factory ImageProduit.fromJson(Map<String, dynamic> json) => _$ImageProduitFromJson(json);
  Map<String, dynamic> toJson() => _$ImageProduitToJson(this);
}

@JsonSerializable()
class CataloguePage {
  final int count;
  final String? next;
  final String? previous;
  final List<Produit> results;

  const CataloguePage({required this.count, this.next, this.previous, required this.results});
  bool get hasMore => next != null;
  factory CataloguePage.fromJson(Map<String, dynamic> json) => _$CataloguePageFromJson(json);
  Map<String, dynamic> toJson() => _$CataloguePageToJson(this);
}
```

### `lib/models/commande.dart`

```dart
import 'package:json_annotation/json_annotation.dart';
part 'commande.g.dart';

@JsonSerializable()
class CommandeDetail {
  final int id;
  @JsonKey(name: 'produit')         final String? produitNom;
  @JsonKey(name: 'prix_unitaire')   final String prixUnitaire;
  final int quantite;
  @JsonKey(name: 'unite_vente')     final String uniteVente;
  @JsonKey(name: 'sous_total')      final String sousTotal;

  const CommandeDetail({
    required this.id,
    this.produitNom,
    required this.prixUnitaire,
    required this.quantite,
    required this.uniteVente,
    required this.sousTotal,
  });
  factory CommandeDetail.fromJson(Map<String, dynamic> json) => _$CommandeDetailFromJson(json);
  Map<String, dynamic> toJson() => _$CommandeDetailToJson(this);
}

@JsonSerializable()
class Commande {
  @JsonKey(name: 'numero_commande')     final String numeroCommande;
  final String statut;
  @JsonKey(name: 'statut_label')        final String? statutLabel;
  @JsonKey(name: 'statut_paiement')     final String? statutPaiement;
  @JsonKey(name: 'methode_paiement')    final String? methodePaiement;
  @JsonKey(name: 'mode_livraison')      final String? modeLivraison;
  @JsonKey(name: 'sous_total')          final String? sousTotal;
  @JsonKey(name: 'frais_livraison')     final String? fraisLivraison;
  final String? remise;
  final String? total;
  final String? producteur;
  final String? acheteur;
  @JsonKey(name: 'adresse_livraison')   final String? adresseLivraison;
  @JsonKey(name: 'notes_acheteur')      final String? notesAcheteur;
  @JsonKey(name: 'created_at')          final String createdAt;
  @JsonKey(name: 'date_livraison_prevue') final String? dateLivraisonPrevue;
  final List<CommandeDetail>? details;

  const Commande({
    required this.numeroCommande,
    required this.statut,
    this.statutLabel,
    this.statutPaiement,
    this.methodePaiement,
    this.modeLivraison,
    this.sousTotal,
    this.fraisLivraison,
    this.remise,
    this.total,
    this.producteur,
    this.acheteur,
    this.adresseLivraison,
    this.notesAcheteur,
    required this.createdAt,
    this.dateLivraisonPrevue,
    this.details,
  });

  bool get estAnnulable => statut == 'en_attente' || statut == 'confirmee';

  factory Commande.fromJson(Map<String, dynamic> json) => _$CommandeFromJson(json);
  Map<String, dynamic> toJson() => _$CommandeToJson(this);
}
```

### `lib/models/panier.dart`

```dart
import 'package:json_annotation/json_annotation.dart';
part 'panier.g.dart';

@JsonSerializable()
class LignePanier {
  final int? id;
  final String slug;
  final String nom;
  final int quantite;
  @JsonKey(name: 'prix_unitaire')   final String prixUnitaire;
  @JsonKey(name: 'sous_total')      final dynamic sousTotal;
  @JsonKey(name: 'unite_vente')     final String uniteVente;
  @JsonKey(name: 'unite_vente_label') final String? uniteVenteLabel;
  @JsonKey(name: 'producteur_id')   final int? producteurId;
  @JsonKey(name: 'producteur_nom')  final String? producteurNom;
  final String? image;
  @JsonKey(name: 'stock_reel')      final int? stockReel;

  const LignePanier({
    this.id,
    required this.slug,
    required this.nom,
    required this.quantite,
    required this.prixUnitaire,
    required this.sousTotal,
    required this.uniteVente,
    this.uniteVenteLabel,
    this.producteurId,
    this.producteurNom,
    this.image,
    this.stockReel,
  });

  factory LignePanier.fromJson(Map<String, dynamic> json) => _$LignePanierFromJson(json);
  Map<String, dynamic> toJson() => _$LignePanierToJson(this);
}

@JsonSerializable()
class Panier {
  final List<LignePanier> items;
  final dynamic total;
  @JsonKey(name: 'nb_articles') final int nbArticles;
  @JsonKey(name: 'nb_items')    final int nbItems;
  final List<Map<String, dynamic>>? producteurs;

  const Panier({
    required this.items,
    required this.total,
    required this.nbArticles,
    required this.nbItems,
    this.producteurs,
  });

  factory Panier.fromJson(Map<String, dynamic> json) => _$PanierFromJson(json);
  Map<String, dynamic> toJson() => _$PanierToJson(this);
}
```

### `lib/models/adresse.dart`

```dart
import 'package:json_annotation/json_annotation.dart';
part 'adresse.g.dart';

@JsonSerializable()
class Adresse {
  final int id;
  final String? libelle;
  @JsonKey(name: 'nom_complet')     final String? nomComplet;
  final String? telephone;
  final String rue;
  final String commune;
  final String departement;
  @JsonKey(name: 'section_communale') final String? sectionCommunale;
  final String? details;
  @JsonKey(name: 'type_adresse')    final String typeAdresse;
  @JsonKey(name: 'is_default')      final bool isDefault;

  const Adresse({
    required this.id,
    this.libelle,
    this.nomComplet,
    this.telephone,
    required this.rue,
    required this.commune,
    required this.departement,
    this.sectionCommunale,
    this.details,
    required this.typeAdresse,
    required this.isDefault,
  });

  factory Adresse.fromJson(Map<String, dynamic> json) => _$AdresseFromJson(json);
  Map<String, dynamic> toJson() => _$AdresseToJson(this);
}
```

### `lib/models/producteur_profil.dart`

```dart
import 'package:json_annotation/json_annotation.dart';
part 'producteur_profil.g.dart';

@JsonSerializable()
class ProducteurStats {
  @JsonKey(name: 'nb_commandes_total')    final int nbCommandesTotal;
  @JsonKey(name: 'nb_commandes_attente')  final int nbCommandesAttente;
  @JsonKey(name: 'chiffre_affaires')      final dynamic chiffreAffaires;
  @JsonKey(name: 'nb_produits_actifs')    final int nbProduitsActifs;
  @JsonKey(name: 'nb_collectes')          final int? nbCollectes;

  const ProducteurStats({
    required this.nbCommandesTotal,
    required this.nbCommandesAttente,
    required this.chiffreAffaires,
    required this.nbProduitsActifs,
    this.nbCollectes,
  });

  factory ProducteurStats.fromJson(Map<String, dynamic> json) => _$ProducteurStatsFromJson(json);
  Map<String, dynamic> toJson() => _$ProducteurStatsToJson(this);
}

@JsonSerializable()
class ProducteurProfil {
  final int id;
  @JsonKey(name: 'nom_complet')       final String nomComplet;
  @JsonKey(name: 'first_name')        final String? firstName;
  @JsonKey(name: 'last_name')         final String? lastName;
  final String? email;
  final String? telephone;
  final String? photo;
  @JsonKey(name: 'code_producteur')   final String codeProducteur;
  final String departement;
  @JsonKey(name: 'departement_label') final String? departementLabel;
  final String commune;
  final String? localite;
  @JsonKey(name: 'superficie_ha')     final String? superficieHa;
  final String? description;
  @JsonKey(name: 'num_identification') final String? numIdentification;
  final String statut;
  @JsonKey(name: 'statut_label')      final String? statutLabel;
  @JsonKey(name: 'nb_produits_actifs') final int? nbProduitsActifs;
  @JsonKey(name: 'nb_commandes_total') final int? nbCommandesTotal;

  const ProducteurProfil({
    required this.id,
    required this.nomComplet,
    this.firstName,
    this.lastName,
    this.email,
    this.telephone,
    this.photo,
    required this.codeProducteur,
    required this.departement,
    this.departementLabel,
    required this.commune,
    this.localite,
    this.superficieHa,
    this.description,
    this.numIdentification,
    required this.statut,
    this.statutLabel,
    this.nbProduitsActifs,
    this.nbCommandesTotal,
  });

  factory ProducteurProfil.fromJson(Map<String, dynamic> json) => _$ProducteurProfilFromJson(json);
  Map<String, dynamic> toJson() => _$ProducteurProfilToJson(this);
}
```

---

## 4. Service API

### `lib/services/api_service.dart`

```dart
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../core/constants.dart';

class ApiService {
  static ApiService? _instance;
  late final Dio _dio;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  ApiService._() {
    _dio = Dio(BaseOptions(
      baseUrl: AppConstants.apiUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));
    _dio.interceptors.add(_authInterceptor());
  }

  static ApiService get instance => _instance ??= ApiService._();

  InterceptorsWrapper _authInterceptor() {
    return InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: AppConstants.keyAccess);
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (DioException error, handler) async {
        if (error.response?.statusCode == 401) {
          // Tentative de rafraîchissement du token
          final refreshed = await _refreshToken();
          if (refreshed) {
            // Relancer la requête originale
            final opts = error.requestOptions;
            final token = await _storage.read(key: AppConstants.keyAccess);
            opts.headers['Authorization'] = 'Bearer $token';
            try {
              final response = await _dio.fetch(opts);
              handler.resolve(response);
              return;
            } catch (_) {}
          }
          // Échec → déconnecter l'utilisateur
          await _storage.deleteAll();
        }
        handler.next(error);
      },
    );
  }

  Future<bool> _refreshToken() async {
    try {
      final refresh = await _storage.read(key: AppConstants.keyRefresh);
      if (refresh == null) return false;
      final res = await Dio().post(
        '${AppConstants.apiUrl}/auth/token/refresh/',
        data: {'refresh': refresh},
      );
      await _storage.write(key: AppConstants.keyAccess,  value: res.data['access']);
      await _storage.write(key: AppConstants.keyRefresh, value: res.data['refresh']);
      return true;
    } catch (_) {
      return false;
    }
  }

  Dio get dio => _dio;

  // ─── AUTH ────────────────────────────────────────────────────────────────

  Future<Response> login(String email, String password) =>
      _dio.post('/auth/login/', data: {'email': email, 'password': password});

  Future<Response> register(Map<String, dynamic> data) =>
      _dio.post('/auth/register/', data: data);

  Future<Response> logout(String refresh, {String? fcmToken}) =>
      _dio.post('/auth/logout/', data: {
        'refresh': refresh,
        if (fcmToken != null) 'fcm_token': fcmToken,
      });

  Future<Response> getMe() => _dio.get('/auth/me/');

  Future<Response> updateMe(FormData data) =>
      _dio.patch('/auth/me/', data: data);

  Future<Response> changePassword(String current, String next) =>
      _dio.post('/auth/change-password/', data: {
        'current_password': current,
        'new_password': next,
      });

  Future<Response> refreshTokenReq(String refresh) =>
      _dio.post('/auth/token/refresh/', data: {'refresh': refresh});

  Future<Response> registerFcmToken(String fcmToken) =>
      _dio.post('/auth/fcm-token/', data: {'fcm_token': fcmToken});

  // ─── CATALOGUE ───────────────────────────────────────────────────────────

  Future<Response> getCatalogue({
    int page = 1,
    String? search,
    String? categorieSlug,
    String? departement,
    int? producteurId,
    double? prixMin,
    double? prixMax,
    bool? featured,
  }) =>
      _dio.get('/products/', queryParameters: {
        'page': page,
        'page_size': AppConstants.pageSize,
        if (search != null && search.isNotEmpty) 'search': search,
        if (categorieSlug != null) 'categorie': categorieSlug,
        if (departement != null) 'departement': departement,
        if (producteurId != null) 'producteur_id': producteurId,
        if (prixMin != null) 'prix_min': prixMin,
        if (prixMax != null) 'prix_max': prixMax,
        if (featured == true) 'featured': '1',
      });

  Future<Response> getCategories() => _dio.get('/products/categories/');

  Future<Response> getProduitDetail(String slug) =>
      _dio.get('/products/public/$slug/');

  // ─── CATALOGUE PRODUCTEUR ─────────────────────────────────────────────

  Future<Response> getMesProduits({int page = 1, String? search}) =>
      _dio.get('/products/mes-produits/', queryParameters: {
        'page': page,
        if (search != null) 'search': search,
      });

  Future<Response> createProduit(FormData data) =>
      _dio.post('/products/mes-produits/', data: data);

  Future<Response> updateProduit(String slug, FormData data) =>
      _dio.patch('/products/mes-produits/$slug/', data: data);

  Future<Response> deleteProduit(String slug) =>
      _dio.delete('/products/mes-produits/$slug/');

  // ─── PANIER ──────────────────────────────────────────────────────────────

  Future<Response> getPanier() => _dio.get('/orders/panier/');

  Future<Response> ajouterAuPanier(String slug, int quantite) =>
      _dio.post('/orders/panier/ajouter/', data: {'slug': slug, 'quantite': quantite});

  Future<Response> modifierQuantite(String slug, int quantite) =>
      _dio.patch('/orders/panier/modifier/$slug/', data: {'quantite': quantite});

  Future<Response> retirerDuPanier(String slug) =>
      _dio.delete('/orders/panier/retirer/$slug/');

  Future<Response> viderPanier() => _dio.delete('/orders/panier/vider/');

  // ─── COMMANDES ───────────────────────────────────────────────────────────

  Future<Response> passerCommande(Map<String, dynamic> data) =>
      _dio.post('/orders/commander/', data: data);

  Future<Response> getMesCommandes({String? statut}) =>
      _dio.get('/auth/commandes/', queryParameters: {
        if (statut != null) 'statut': statut,
      });

  Future<Response> getCommandeDetail(String numero) =>
      _dio.get('/auth/commandes/$numero/');

  // ─── PRODUCTEUR ──────────────────────────────────────────────────────────

  Future<Response> getProducteurStats() =>
      _dio.get('/auth/producteur/stats/');

  Future<Response> getProducteurProfil() =>
      _dio.get('/auth/producteur/profil/');

  Future<Response> updateProducteurProfil(FormData data) =>
      _dio.patch('/auth/producteur/profil/', data: data);

  Future<Response> getCommandesProducteur({String? statut}) =>
      _dio.get('/auth/producteur/commandes/', queryParameters: {
        if (statut != null) 'statut': statut,
      });

  Future<Response> getCommandeProducteurDetail(String numero) =>
      _dio.get('/auth/producteur/commandes/$numero/');

  Future<Response> changerStatutCommande(String numero, String action, {String? motif}) =>
      _dio.patch('/auth/producteur/commandes/$numero/statut/', data: {
        'action': action,
        if (motif != null) 'motif': motif,
      });

  // ─── ADRESSES ────────────────────────────────────────────────────────────

  Future<Response> getAdresses() => _dio.get('/auth/adresses/');
  Future<Response> createAdresse(Map<String, dynamic> data) =>
      _dio.post('/auth/adresses/', data: data);
  Future<Response> updateAdresse(int id, Map<String, dynamic> data) =>
      _dio.patch('/auth/adresses/$id/', data: data);
  Future<Response> deleteAdresse(int id) =>
      _dio.delete('/auth/adresses/$id/');
  Future<Response> setAdresseDefault(int id) =>
      _dio.post('/auth/adresses/$id/default/');

  // ─── COLLECTES ───────────────────────────────────────────────────────────

  Future<Response> getMesParticipations() =>
      _dio.get('/collectes/mes-participations/');

  Future<Response> confirmerParticipation(int id) =>
      _dio.patch('/collectes/participations/$id/confirmer/');

  // ─── GÉO ─────────────────────────────────────────────────────────────────

  Future<Response> getDepartements() => _dio.get('/geo/departements/');
  Future<Response> getCommunes(String deptSlug) =>
      _dio.get('/geo/communes/', queryParameters: {'dept': deptSlug});
  Future<Response> getSections(String deptSlug, String commune) =>
      _dio.get('/geo/sections/', queryParameters: {'dept': deptSlug, 'commune': commune});
  Future<Response> rechercheGeo(String q) =>
      _dio.get('/geo/recherche/', queryParameters: {'q': q});
}
```

---

## 5. Login

> Écran correspondant à `templates/accounts/login.html`

```dart
// lib/screens/auth/login_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:convert';
import '../../services/api_service.dart';
import '../../models/user.dart';
import '../../core/constants.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey   = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  final _passCtrl  = TextEditingController();
  bool _loading    = false;
  bool _obscure    = true;
  String? _error;

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _loading = true; _error = null; });
    try {
      final res  = await ApiService.instance.login(_emailCtrl.text.trim(), _passCtrl.text);
      final auth = AuthResponse.fromJson(res.data as Map<String, dynamic>);

      const storage = FlutterSecureStorage();
      await storage.write(key: AppConstants.keyAccess,  value: auth.access);
      await storage.write(key: AppConstants.keyRefresh, value: auth.refresh);
      await storage.write(key: AppConstants.keyUser,    value: jsonEncode(auth.user.toJson()));

      if (!mounted) return;
      _redirectByRole(auth.user);
    } catch (e) {
      setState(() => _error = 'Email ou mot de passe incorrect.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _redirectByRole(User user) {
    if (user.isSuperAdmin) {
      context.go('/admin');
    } else if (user.isProducteur) {
      if (user.isProducteurActif) {
        context.go('/producteur');
      } else {
        context.go('/producteur/en-attente');
      }
    } else {
      context.go('/');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7F2),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 400),
            child: Card(
              elevation: 4,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Logo
                      Center(
                        child: Image.asset('assets/images/logo.png', height: 72),
                      ),
                      const SizedBox(height: 8),
                      const Center(
                        child: Text('Makèt Peyizan',
                          style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF2E7D32))),
                      ),
                      const SizedBox(height: 32),

                      // Email
                      TextFormField(
                        controller: _emailCtrl,
                        keyboardType: TextInputType.emailAddress,
                        decoration: const InputDecoration(
                          labelText: 'Email',
                          prefixIcon: Icon(Icons.email_outlined),
                          border: OutlineInputBorder(),
                        ),
                        validator: (v) => (v == null || !v.contains('@')) ? 'Email invalide' : null,
                      ),
                      const SizedBox(height: 16),

                      // Mot de passe
                      TextFormField(
                        controller: _passCtrl,
                        obscureText: _obscure,
                        decoration: InputDecoration(
                          labelText: 'Mot de passe',
                          prefixIcon: const Icon(Icons.lock_outline),
                          suffixIcon: IconButton(
                            icon: Icon(_obscure ? Icons.visibility_off : Icons.visibility),
                            onPressed: () => setState(() => _obscure = !_obscure),
                          ),
                          border: const OutlineInputBorder(),
                        ),
                        validator: (v) => (v == null || v.length < 6) ? 'Mot de passe requis' : null,
                      ),
                      const SizedBox(height: 8),

                      // Erreur
                      if (_error != null)
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.red.shade50,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: Colors.red.shade200),
                          ),
                          child: Text(_error!, style: TextStyle(color: Colors.red.shade800)),
                        ),
                      const SizedBox(height: 24),

                      // Bouton
                      ElevatedButton(
                        onPressed: _loading ? null : _submit,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF2E7D32),
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        child: _loading
                            ? const SizedBox(height: 20, width: 20,
                                child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                            : const Text('Se connecter', style: TextStyle(color: Colors.white, fontSize: 16)),
                      ),
                      const SizedBox(height: 16),

                      // Lien inscription
                      TextButton(
                        onPressed: () => context.go('/inscription'),
                        child: const Text("Pas encore de compte ? S'inscrire"),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
```

---

## 6. Inscription

> Écran correspondant à `templates/accounts/register.html`

```dart
// lib/screens/auth/register_screen.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:convert';
import '../../services/api_service.dart';
import '../../models/user.dart';
import '../../core/constants.dart';
import '../widgets/geo_selector.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});
  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> with SingleTickerProviderStateMixin {
  final _formKey       = GlobalKey<FormState>();
  late TabController   _tabCtrl;
  String _role         = 'acheteur';
  bool _loading        = false;
  bool _obscure        = true;
  String? _error;

  // Champs communs
  final _firstNameCtrl = TextEditingController();
  final _lastNameCtrl  = TextEditingController();
  final _emailCtrl     = TextEditingController();
  final _telCtrl       = TextEditingController();
  final _passCtrl      = TextEditingController();
  final _pass2Ctrl     = TextEditingController();

  // Champs producteur
  String? _departement;
  String? _commune;
  String? _localite;
  final _superficieCtrl   = TextEditingController();
  final _descriptionCtrl  = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tabCtrl = TabController(length: 2, vsync: this);
    _tabCtrl.addListener(() {
      setState(() => _role = _tabCtrl.index == 0 ? 'acheteur' : 'producteur');
    });
  }

  @override
  void dispose() {
    _tabCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_role == 'producteur' && (_departement == null || _commune == null)) {
      setState(() => _error = 'Veuillez sélectionner votre département et commune.');
      return;
    }
    setState(() { _loading = true; _error = null; });

    final data = <String, dynamic>{
      'username':   _emailCtrl.text.split('@').first + DateTime.now().millisecondsSinceEpoch.toString().substring(8),
      'email':      _emailCtrl.text.trim(),
      'password':   _passCtrl.text,
      'password2':  _pass2Ctrl.text,
      'first_name': _firstNameCtrl.text.trim(),
      'last_name':  _lastNameCtrl.text.trim(),
      'telephone':  _telCtrl.text.trim(),
      'role':       _role,
    };

    if (_role == 'producteur') {
      data['departement'] = _departement!;
      data['commune']     = _commune!;
      if (_localite?.isNotEmpty == true) data['localite'] = _localite;
      if (_superficieCtrl.text.isNotEmpty) data['superficie_ha'] = _superficieCtrl.text;
      if (_descriptionCtrl.text.isNotEmpty) data['description'] = _descriptionCtrl.text;
    }

    try {
      final res  = await ApiService.instance.register(data);
      final auth = AuthResponse.fromJson(res.data as Map<String, dynamic>);

      const storage = FlutterSecureStorage();
      await storage.write(key: AppConstants.keyAccess,  value: auth.access);
      await storage.write(key: AppConstants.keyRefresh, value: auth.refresh);
      await storage.write(key: AppConstants.keyUser,    value: jsonEncode(auth.user.toJson()));

      if (!mounted) return;
      if (_role == 'producteur') {
        context.go('/producteur/en-attente');
      } else {
        context.go('/');
      }
    } catch (e) {
      final detail = _parseError(e);
      setState(() => _error = detail);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _parseError(dynamic e) {
    try {
      final data = (e as dynamic).response?.data;
      if (data is Map) {
        final msgs = <String>[];
        data.forEach((k, v) {
          if (v is List) msgs.add('$k: ${v.join(', ')}');
          else msgs.add('$k: $v');
        });
        return msgs.join('\n');
      }
    } catch (_) {}
    return 'Une erreur est survenue. Veuillez réessayer.';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("S'inscrire"),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          // Onglets rôle
          Container(
            color: const Color(0xFF2E7D32),
            child: TabBar(
              controller: _tabCtrl,
              indicatorColor: Colors.white,
              labelColor: Colors.white,
              unselectedLabelColor: Colors.white60,
              tabs: const [
                Tab(icon: Icon(Icons.shopping_cart_outlined), text: 'Acheteur'),
                Tab(icon: Icon(Icons.agriculture_outlined),  text: 'Producteur'),
              ],
            ),
          ),

          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Champs communs
                    Row(children: [
                      Expanded(child: _field(_firstNameCtrl, 'Prénom', required: true)),
                      const SizedBox(width: 12),
                      Expanded(child: _field(_lastNameCtrl, 'Nom', required: true)),
                    ]),
                    const SizedBox(height: 16),
                    _field(_emailCtrl, 'Email', type: TextInputType.emailAddress, required: true,
                      validator: (v) => (v == null || !v.contains('@')) ? 'Email invalide' : null),
                    const SizedBox(height: 16),
                    _field(_telCtrl, 'Téléphone (+509...)', type: TextInputType.phone),
                    const SizedBox(height: 16),
                    _passwordField(_passCtrl, 'Mot de passe'),
                    const SizedBox(height: 16),
                    _passwordField(_pass2Ctrl, 'Confirmer le mot de passe',
                      validator: (v) => v != _passCtrl.text ? 'Les mots de passe ne correspondent pas' : null),
                    const SizedBox(height: 24),

                    // Champs spécifiques producteur
                    if (_role == 'producteur') ...[
                      const Divider(),
                      const Text('Informations agricoles',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                      const SizedBox(height: 16),
                      GeoSelector(
                        onChanged: ({required dept, required commune, section}) {
                          setState(() { _departement = dept; _commune = commune; });
                        },
                      ),
                      const SizedBox(height: 16),
                      _field(_superficieCtrl, 'Superficie (ha)', type: TextInputType.number),
                      const SizedBox(height: 16),
                      TextFormField(
                        controller: _descriptionCtrl,
                        maxLines: 3,
                        decoration: const InputDecoration(
                          labelText: 'Description de votre exploitation',
                          border: OutlineInputBorder(),
                        ),
                      ),
                    ],

                    if (_error != null) ...[
                      const SizedBox(height: 16),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.red.shade50,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.red.shade200),
                        ),
                        child: Text(_error!, style: TextStyle(color: Colors.red.shade800)),
                      ),
                    ],
                    const SizedBox(height: 24),

                    ElevatedButton(
                      onPressed: _loading ? null : _submit,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF2E7D32),
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      child: _loading
                          ? const SizedBox(height: 20, width: 20,
                              child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                          : const Text("Créer mon compte",
                              style: TextStyle(color: Colors.white, fontSize: 16)),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _field(TextEditingController ctrl, String label, {
    TextInputType type = TextInputType.text,
    bool required = false,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: ctrl,
      keyboardType: type,
      decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
      validator: validator ?? (required ? (v) => (v == null || v.isEmpty) ? 'Champ requis' : null : null),
    );
  }

  Widget _passwordField(TextEditingController ctrl, String label, {String? Function(String?)? validator}) {
    return TextFormField(
      controller: ctrl,
      obscureText: _obscure,
      decoration: InputDecoration(
        labelText: label,
        border: const OutlineInputBorder(),
        suffixIcon: IconButton(
          icon: Icon(_obscure ? Icons.visibility_off : Icons.visibility),
          onPressed: () => setState(() => _obscure = !_obscure),
        ),
      ),
      validator: validator ?? (v) => (v == null || v.length < 8) ? 'Minimum 8 caractères' : null,
    );
  }
}
```

---

## 7. Catalogue — Liste

> Écran correspondant à `templates/home/index.html` et la section catalogue

```dart
// lib/screens/catalogue/catalogue_screen.dart
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../../services/api_service.dart';
import '../../models/produit.dart';
import '../../core/constants.dart';
import 'produit_detail_screen.dart';

class CatalogueScreen extends StatefulWidget {
  const CatalogueScreen({super.key});
  @override
  State<CatalogueScreen> createState() => _CatalogueScreenState();
}

class _CatalogueScreenState extends State<CatalogueScreen> {
  final _searchCtrl   = TextEditingController();
  final _scrollCtrl   = ScrollController();
  List<Produit>       _produits = [];
  List<Categorie>     _categories = [];
  String?             _categorieSlug;
  int                 _page = 1;
  bool                _loading = false;
  bool                _hasMore = true;

  @override
  void initState() {
    super.initState();
    _loadCategories();
    _load(reset: true);
    _scrollCtrl.addListener(() {
      if (_scrollCtrl.position.pixels >= _scrollCtrl.position.maxScrollExtent - 200) {
        _load();
      }
    });
  }

  @override
  void dispose() {
    _scrollCtrl.dispose();
    _searchCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadCategories() async {
    try {
      final res = await ApiService.instance.getCategories();
      final list = (res.data as List).map((e) => Categorie.fromJson(e as Map<String, dynamic>)).toList();
      setState(() => _categories = list);
    } catch (_) {}
  }

  Future<void> _load({bool reset = false}) async {
    if (_loading || (!_hasMore && !reset)) return;
    setState(() => _loading = true);
    if (reset) { _page = 1; _hasMore = true; }

    try {
      final res  = await ApiService.instance.getCatalogue(
        page: _page,
        search: _searchCtrl.text.trim().isEmpty ? null : _searchCtrl.text.trim(),
        categorieSlug: _categorieSlug,
      );
      final page = CataloguePage.fromJson(res.data as Map<String, dynamic>);
      setState(() {
        if (reset) _produits = page.results;
        else       _produits.addAll(page.results);
        _hasMore = page.hasMore;
        _page++;
      });
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7F2),
      appBar: AppBar(
        title: const Text('Makèt Peyizan'),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
        actions: [
          IconButton(icon: const Icon(Icons.shopping_cart_outlined), onPressed: () => Navigator.pushNamed(context, '/panier')),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
            child: TextField(
              controller: _searchCtrl,
              decoration: InputDecoration(
                hintText: 'Rechercher un produit...',
                filled: true,
                fillColor: Colors.white,
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchCtrl.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () { _searchCtrl.clear(); _load(reset: true); })
                    : null,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
                contentPadding: const EdgeInsets.symmetric(vertical: 8),
              ),
              onSubmitted: (_) => _load(reset: true),
            ),
          ),
        ),
      ),
      body: Column(
        children: [
          // Filtre catégories
          if (_categories.isNotEmpty)
            SizedBox(
              height: 50,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                itemCount: _categories.length + 1,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (_, i) {
                  if (i == 0) {
                    return _catChip('Tout', null);
                  }
                  final cat = _categories[i - 1];
                  return _catChip(cat.nom, cat.slug);
                },
              ),
            ),

          // Grille produits
          Expanded(
            child: RefreshIndicator(
              onRefresh: () => _load(reset: true),
              child: GridView.builder(
                controller: _scrollCtrl,
                padding: const EdgeInsets.all(12),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  mainAxisSpacing: 12,
                  crossAxisSpacing: 12,
                  childAspectRatio: 0.72,
                ),
                itemCount: _produits.length + (_hasMore ? 1 : 0),
                itemBuilder: (_, i) {
                  if (i == _produits.length) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  return _ProduitCard(produit: _produits[i]);
                },
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _catChip(String label, String? slug) {
    final selected = _categorieSlug == slug;
    return FilterChip(
      label: Text(label),
      selected: selected,
      selectedColor: const Color(0xFF2E7D32),
      labelStyle: TextStyle(color: selected ? Colors.white : null),
      onSelected: (_) {
        setState(() => _categorieSlug = slug);
        _load(reset: true);
      },
    );
  }
}

class _ProduitCard extends StatelessWidget {
  final Produit produit;
  const _ProduitCard({required this.produit});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => Navigator.push(context,
          MaterialPageRoute(builder: (_) => ProduitDetailScreen(slug: produit.slug))),
      child: Card(
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Image
            ClipRRect(
              borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
              child: AspectRatio(
                aspectRatio: 1,
                child: CachedNetworkImage(
                  imageUrl: imageUrl(produit.imagePrincipale),
                  fit: BoxFit.cover,
                  placeholder: (_, __) => Container(color: const Color(0xFFE8F5E9),
                      child: const Center(child: Icon(Icons.image_outlined, color: Colors.green))),
                  errorWidget: (_, __, ___) => Container(color: const Color(0xFFE8F5E9),
                      child: const Center(child: Icon(Icons.agriculture, color: Colors.green))),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(produit.nom,
                    maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                  const SizedBox(height: 4),
                  Text('${produit.prixUnitaire} HTG / ${produit.uniteVenteLabel ?? produit.uniteVente}',
                    style: const TextStyle(color: Color(0xFF2E7D32), fontWeight: FontWeight.bold, fontSize: 12)),
                  if (produit.producteur != null) ...[
                    const SizedBox(height: 4),
                    Text(produit.producteur!.nom,
                      style: const TextStyle(color: Colors.grey, fontSize: 11),
                      maxLines: 1, overflow: TextOverflow.ellipsis),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

---

## 8. Catalogue — Détail produit

> Écran correspondant à `templates/home/produit_detail.html`

```dart
// lib/screens/catalogue/produit_detail_screen.dart
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../../services/api_service.dart';
import '../../models/produit.dart';
import '../../core/constants.dart';

class ProduitDetailScreen extends StatefulWidget {
  final String slug;
  const ProduitDetailScreen({super.key, required this.slug});
  @override
  State<ProduitDetailScreen> createState() => _ProduitDetailScreenState();
}

class _ProduitDetailScreenState extends State<ProduitDetailScreen> {
  Produit? _produit;
  bool _loading = true;
  int _quantite = 1;
  bool _ajoutEnCours = false;
  int _imageIndex = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final res = await ApiService.instance.getProduitDetail(widget.slug);
      setState(() {
        _produit = Produit.fromJson(res.data as Map<String, dynamic>);
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  Future<void> _ajouterAuPanier() async {
    if (_produit == null) return;
    setState(() => _ajoutEnCours = true);
    try {
      await ApiService.instance.ajouterAuPanier(_produit!.slug, _quantite);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${_produit!.nom} ajouté au panier !'),
          backgroundColor: const Color(0xFF2E7D32),
          action: SnackBarAction(
            label: 'Voir',
            textColor: Colors.white,
            onPressed: () => Navigator.pushNamed(context, '/panier'),
          ),
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Erreur. Veuillez vous connecter.'), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _ajoutEnCours = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    if (_produit == null) return const Scaffold(body: Center(child: Text('Produit introuvable')));

    final p = _produit!;
    final allImages = [if (p.imagePrincipale != null) p.imagePrincipale!, ...?(p.images?.map((i) => i.image))];

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: Text(p.nom, overflow: TextOverflow.ellipsis),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
        actions: [
          IconButton(icon: const Icon(Icons.shopping_cart_outlined),
              onPressed: () => Navigator.pushNamed(context, '/panier')),
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Galerie images
            Stack(
              children: [
                AspectRatio(
                  aspectRatio: 1,
                  child: PageView.builder(
                    itemCount: allImages.isEmpty ? 1 : allImages.length,
                    onPageChanged: (i) => setState(() => _imageIndex = i),
                    itemBuilder: (_, i) => allImages.isEmpty
                        ? Container(color: const Color(0xFFE8F5E9),
                            child: const Center(child: Icon(Icons.agriculture, size: 80, color: Colors.green)))
                        : CachedNetworkImage(imageUrl: imageUrl(allImages[i]), fit: BoxFit.cover),
                  ),
                ),
                if (allImages.length > 1)
                  Positioned(
                    bottom: 12,
                    left: 0, right: 0,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: List.generate(allImages.length, (i) => Container(
                        margin: const EdgeInsets.symmetric(horizontal: 3),
                        width: _imageIndex == i ? 12 : 8,
                        height: _imageIndex == i ? 12 : 8,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: _imageIndex == i ? const Color(0xFF2E7D32) : Colors.white70,
                        ),
                      )),
                    ),
                  ),
              ],
            ),

            Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Nom + badge
                  Row(children: [
                    Expanded(child: Text(p.nom, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold))),
                    if (p.isFeatured) Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.amber.shade100,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: const Text('Vedette', style: TextStyle(fontSize: 11, color: Colors.orange)),
                    ),
                  ]),
                  if (p.variete != null) ...[
                    const SizedBox(height: 4),
                    Text(p.variete!, style: const TextStyle(color: Colors.grey)),
                  ],
                  const SizedBox(height: 12),

                  // Prix
                  Text('${p.prixUnitaire} HTG / ${p.uniteVenteLabel ?? p.uniteVente}',
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF2E7D32))),
                  if (p.prixGros != null)
                    Text('Prix gros : ${p.prixGros} HTG',
                      style: const TextStyle(color: Colors.grey, fontSize: 13)),
                  const SizedBox(height: 16),

                  // Stock
                  Row(children: [
                    Icon(
                      (p.stockReel ?? p.stockDisponible) > 0 ? Icons.check_circle : Icons.cancel,
                      color: (p.stockReel ?? p.stockDisponible) > 0 ? Colors.green : Colors.red,
                      size: 16,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      (p.stockReel ?? p.stockDisponible) > 0
                          ? 'Stock disponible : ${p.stockReel ?? p.stockDisponible} ${p.uniteVente}'
                          : 'Épuisé',
                      style: TextStyle(
                        color: (p.stockReel ?? p.stockDisponible) > 0 ? Colors.green.shade700 : Colors.red,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ]),
                  const SizedBox(height: 20),

                  // Description
                  if (p.description?.isNotEmpty == true) ...[
                    const Text('Description', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const SizedBox(height: 8),
                    Text(p.description!, style: const TextStyle(height: 1.6)),
                    const SizedBox(height: 20),
                  ],

                  // Infos producteur
                  if (p.producteur != null) ...[
                    const Divider(),
                    const SizedBox(height: 12),
                    const Text('Producteur', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const SizedBox(height: 8),
                    Row(children: [
                      const Icon(Icons.person_outline, color: Colors.grey),
                      const SizedBox(width: 8),
                      Text(p.producteur!.nom, style: const TextStyle(fontWeight: FontWeight.w500)),
                    ]),
                    const SizedBox(height: 4),
                    Row(children: [
                      const Icon(Icons.location_on_outlined, color: Colors.grey),
                      const SizedBox(width: 8),
                      Text('${p.producteur!.commune ?? ''}, ${p.producteur!.departement ?? ''}',
                        style: const TextStyle(color: Colors.grey)),
                    ]),
                    const SizedBox(height: 20),
                  ],

                  // Sélecteur quantité + Ajouter au panier
                  if ((p.stockReel ?? p.stockDisponible) > 0) ...[
                    const Divider(),
                    const SizedBox(height: 16),
                    Row(children: [
                      const Text('Quantité :', style: TextStyle(fontWeight: FontWeight.w500)),
                      const Spacer(),
                      IconButton(
                        onPressed: _quantite > p.quantiteMinCommande
                            ? () => setState(() => _quantite--)
                            : null,
                        icon: const Icon(Icons.remove_circle_outline),
                        color: const Color(0xFF2E7D32),
                      ),
                      Text('$_quantite', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      IconButton(
                        onPressed: _quantite < (p.stockReel ?? p.stockDisponible)
                            ? () => setState(() => _quantite++)
                            : null,
                        icon: const Icon(Icons.add_circle_outline),
                        color: const Color(0xFF2E7D32),
                      ),
                    ]),
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: _ajoutEnCours ? null : _ajouterAuPanier,
                        icon: _ajoutEnCours
                            ? const SizedBox(width: 18, height: 18,
                                child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                            : const Icon(Icons.add_shopping_cart),
                        label: const Text('Ajouter au panier'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF2E7D32),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

---

## 9. Panier

> Écran correspondant à `templates/home/panier.html`

```dart
// lib/screens/orders/panier_screen.dart
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../../services/api_service.dart';
import '../../models/panier.dart';
import '../../core/constants.dart';

class PanierScreen extends StatefulWidget {
  const PanierScreen({super.key});
  @override
  State<PanierScreen> createState() => _PanierScreenState();
}

class _PanierScreenState extends State<PanierScreen> {
  Panier? _panier;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final res = await ApiService.instance.getPanier();
      setState(() {
        _panier = Panier.fromJson(res.data as Map<String, dynamic>);
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  Future<void> _modifier(String slug, int delta, int current) async {
    final nouveau = current + delta;
    if (nouveau <= 0) {
      await _retirer(slug);
      return;
    }
    try {
      await ApiService.instance.modifierQuantite(slug, nouveau);
      _load();
    } catch (_) {}
  }

  Future<void> _retirer(String slug) async {
    try {
      await ApiService.instance.retirerDuPanier(slug);
      _load();
    } catch (_) {}
  }

  Future<void> _vider() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Vider le panier'),
        content: const Text('Êtes-vous sûr de vouloir vider votre panier ?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Annuler')),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Vider', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
    if (confirm == true) {
      await ApiService.instance.viderPanier();
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mon Panier'),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
        actions: [
          if (_panier != null && _panier!.items.isNotEmpty)
            IconButton(icon: const Icon(Icons.delete_outline), onPressed: _vider, tooltip: 'Vider'),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _panier == null || _panier!.items.isEmpty
              ? _buildEmpty()
              : _buildPanier(),
    );
  }

  Widget _buildEmpty() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.shopping_cart_outlined, size: 80, color: Colors.grey),
          const SizedBox(height: 16),
          const Text('Votre panier est vide', style: TextStyle(fontSize: 18, color: Colors.grey)),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: () => Navigator.pop(context),
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2E7D32)),
            child: const Text('Parcourir le catalogue', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  Widget _buildPanier() {
    final panier = _panier!;
    return Column(
      children: [
        // Avertissement multi-producteur
        if ((panier.producteurs?.length ?? 0) > 1)
          Container(
            margin: const EdgeInsets.all(12),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.amber.shade50,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.amber.shade300),
            ),
            child: Row(children: [
              const Icon(Icons.info_outline, color: Colors.amber),
              const SizedBox(width: 8),
              const Expanded(child: Text(
                'Votre panier contient des produits de plusieurs producteurs. Une commande sera créée par producteur.',
                style: TextStyle(fontSize: 12),
              )),
            ]),
          ),

        // Liste articles
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.all(12),
            itemCount: panier.items.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (_, i) => _LigneItem(
              ligne: panier.items[i],
              onModifier: _modifier,
              onRetirer: _retirer,
            ),
          ),
        ),

        // Récapitulatif + Commande
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Colors.white,
            boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.08), blurRadius: 8, offset: const Offset(0, -2))],
          ),
          child: Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Total', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  Text('${panier.total} HTG', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF2E7D32))),
                ],
              ),
              Text('${panier.nbArticles} article(s)', style: const TextStyle(color: Colors.grey)),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () => Navigator.pushNamed(context, '/checkout').then((_) => _load()),
                  icon: const Icon(Icons.payment),
                  label: const Text('Passer la commande'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF2E7D32),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _LigneItem extends StatelessWidget {
  final LignePanier ligne;
  final Future<void> Function(String, int, int) onModifier;
  final Future<void> Function(String) onRetirer;

  const _LigneItem({required this.ligne, required this.onModifier, required this.onRetirer});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            // Image
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: SizedBox(
                width: 70, height: 70,
                child: CachedNetworkImage(
                  imageUrl: imageUrl(ligne.image),
                  fit: BoxFit.cover,
                  errorWidget: (_, __, ___) => Container(color: const Color(0xFFE8F5E9),
                      child: const Icon(Icons.agriculture, color: Colors.green)),
                ),
              ),
            ),
            const SizedBox(width: 12),

            // Infos
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(ligne.nom, style: const TextStyle(fontWeight: FontWeight.w600)),
                  Text('${ligne.prixUnitaire} HTG / ${ligne.uniteVente}',
                    style: const TextStyle(color: Colors.grey, fontSize: 12)),
                  Text('${ligne.sousTotal} HTG',
                    style: const TextStyle(color: Color(0xFF2E7D32), fontWeight: FontWeight.bold)),
                ],
              ),
            ),

            // Contrôles quantité
            Column(
              children: [
                Row(
                  children: [
                    IconButton(
                      onPressed: () => onModifier(ligne.slug, -1, ligne.quantite),
                      icon: const Icon(Icons.remove_circle_outline, size: 20),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                    ),
                    Text('${ligne.quantite}',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    IconButton(
                      onPressed: () => onModifier(ligne.slug, 1, ligne.quantite),
                      icon: const Icon(Icons.add_circle_outline, size: 20),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                    ),
                  ],
                ),
                TextButton(
                  onPressed: () => onRetirer(ligne.slug),
                  style: TextButton.styleFrom(foregroundColor: Colors.red, padding: EdgeInsets.zero),
                  child: const Text('Retirer', style: TextStyle(fontSize: 12)),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
```

---

## 10. Checkout

> Écran correspondant à `templates/home/checkout.html`

```dart
// lib/screens/orders/checkout_screen.dart
import 'package:flutter/material.dart';
import '../../services/api_service.dart';
import '../../models/adresse.dart';

class CheckoutScreen extends StatefulWidget {
  const CheckoutScreen({super.key});
  @override
  State<CheckoutScreen> createState() => _CheckoutScreenState();
}

class _CheckoutScreenState extends State<CheckoutScreen> {
  String _methodePaiement = 'cash';
  String _modeLivraison   = 'domicile';
  int? _adresseId;
  final _adresseTextCtrl  = TextEditingController();
  final _villeCtrl        = TextEditingController();
  String? _departement;
  final _notesCtrl        = TextEditingController();
  List<Adresse> _adresses = [];
  bool _loading           = false;
  bool _loadingAdresses   = true;

  final List<Map<String, String>> _methodes = [
    {'value': 'cash',      'label': 'Cash', 'icon': 'attach_money'},
    {'value': 'moncash',   'label': 'MonCash', 'icon': 'phone_android'},
    {'value': 'natcash',   'label': 'NatCash', 'icon': 'phone_android'},
    {'value': 'hors_ligne','label': 'Hors ligne', 'icon': 'cloud_off'},
  ];

  @override
  void initState() {
    super.initState();
    _loadAdresses();
  }

  Future<void> _loadAdresses() async {
    try {
      final res = await ApiService.instance.getAdresses();
      final list = (res.data as List).map((e) => Adresse.fromJson(e as Map<String, dynamic>)).toList();
      setState(() {
        _adresses = list;
        _adresseId = list.where((a) => a.isDefault).isNotEmpty ? list.firstWhere((a) => a.isDefault).id : null;
        _loadingAdresses = false;
      });
    } catch (_) {
      setState(() => _loadingAdresses = false);
    }
  }

  Future<void> _submit() async {
    setState(() => _loading = true);
    try {
      final data = <String, dynamic>{
        'methode_paiement': _methodePaiement,
        'mode_livraison':   _modeLivraison,
        if (_adresseId != null) 'adresse_livraison_id': _adresseId,
        if (_adresseId == null && _adresseTextCtrl.text.isNotEmpty)
          'adresse_livraison_text': _adresseTextCtrl.text.trim(),
        if (_villeCtrl.text.isNotEmpty) 'ville_livraison': _villeCtrl.text.trim(),
        if (_departement != null) 'departement_livraison': _departement,
        if (_notesCtrl.text.isNotEmpty) 'notes': _notesCtrl.text.trim(),
      };

      final res = await ApiService.instance.passerCommande(data);
      if (!mounted) return;

      final commandes = res.data['commandes'] as List? ?? [];
      _showSuccess(commandes.length);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Erreur lors de la commande.'), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _showSuccess(int nb) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: const Text('Commande confirmée !'),
        content: Text('$nb commande(s) créée(s) avec succès. Vous serez contacté pour la livraison.'),
        actions: [
          ElevatedButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              Navigator.pushReplacementNamed(context, '/commandes');
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2E7D32)),
            child: const Text('Voir mes commandes', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Finaliser la commande'),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            // Mode de livraison
            const Text('Mode de livraison', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 12),
            Row(children: [
              _livraisonCard('domicile', 'Livraison', Icons.home_outlined),
              const SizedBox(width: 12),
              _livraisonCard('collecte', 'Point collecte', Icons.store_outlined),
            ]),
            const SizedBox(height: 24),

            // Adresse livraison
            const Text('Adresse de livraison', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 12),
            if (_loadingAdresses)
              const CircularProgressIndicator()
            else if (_adresses.isNotEmpty) ...[
              DropdownButtonFormField<int?>(
                value: _adresseId,
                decoration: const InputDecoration(border: OutlineInputBorder(), labelText: 'Mes adresses'),
                items: [
                  const DropdownMenuItem(value: null, child: Text('Saisir une nouvelle adresse')),
                  ..._adresses.map((a) => DropdownMenuItem(
                    value: a.id,
                    child: Text('${a.libelle ?? a.rue} — ${a.commune}${a.isDefault ? ' (défaut)' : ''}'),
                  )),
                ],
                onChanged: (v) => setState(() => _adresseId = v),
              ),
            ],
            if (_adresseId == null) ...[
              const SizedBox(height: 12),
              TextFormField(
                controller: _adresseTextCtrl,
                decoration: const InputDecoration(labelText: 'Adresse complète', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _villeCtrl,
                decoration: const InputDecoration(labelText: 'Ville / Commune', border: OutlineInputBorder()),
              ),
            ],
            const SizedBox(height: 24),

            // Méthode de paiement
            const Text('Méthode de paiement', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _methodes.map((m) {
                final selected = _methodePaiement == m['value'];
                return ChoiceChip(
                  label: Text(m['label']!),
                  selected: selected,
                  selectedColor: const Color(0xFF2E7D32),
                  labelStyle: TextStyle(color: selected ? Colors.white : null, fontWeight: FontWeight.w500),
                  onSelected: (_) => setState(() => _methodePaiement = m['value']!),
                );
              }).toList(),
            ),
            const SizedBox(height: 24),

            // Notes
            TextFormField(
              controller: _notesCtrl,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: 'Notes pour le producteur (optionnel)',
                border: OutlineInputBorder(),
                hintText: 'Ex: Livrer le matin avant 10h',
              ),
            ),
            const SizedBox(height: 32),

            // Bouton commander
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _loading ? null : _submit,
                icon: _loading
                    ? const SizedBox(width: 18, height: 18,
                        child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : const Icon(Icons.check_circle_outline),
                label: const Text('Confirmer la commande'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF2E7D32),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _livraisonCard(String value, String label, IconData icon) {
    final selected = _modeLivraison == value;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _modeLivraison = value),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: selected ? const Color(0xFFE8F5E9) : Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: selected ? const Color(0xFF2E7D32) : Colors.grey.shade300,
              width: selected ? 2 : 1,
            ),
          ),
          child: Column(children: [
            Icon(icon, color: selected ? const Color(0xFF2E7D32) : Colors.grey, size: 28),
            const SizedBox(height: 4),
            Text(label, style: TextStyle(
              color: selected ? const Color(0xFF2E7D32) : Colors.grey,
              fontWeight: selected ? FontWeight.bold : FontWeight.normal,
            )),
          ]),
        ),
      ),
    );
  }
}
```

---

## 11. Dashboard Acheteur

> Écran correspondant à `templates/dashboard/acheteur.html`

```dart
// lib/screens/dashboard/acheteur/acheteur_dashboard.dart
import 'package:flutter/material.dart';
import '../../../services/api_service.dart';
import '../../../models/commande.dart';

class AcheteurDashboard extends StatefulWidget {
  const AcheteurDashboard({super.key});
  @override
  State<AcheteurDashboard> createState() => _AcheteurDashboardState();
}

class _AcheteurDashboardState extends State<AcheteurDashboard> {
  List<Commande> _commandes = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final res = await ApiService.instance.getMesCommandes();
      final list = (res.data as List)
          .map((e) => Commande.fromJson(e as Map<String, dynamic>))
          .toList();
      setState(() { _commandes = list; _loading = false; });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mon Espace Acheteur'),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Statistiques rapides
                Row(children: [
                  _StatCard('Commandes', '${_commandes.length}', Icons.shopping_bag_outlined, const Color(0xFF2E7D32)),
                  const SizedBox(width: 12),
                  _StatCard(
                    'En cours',
                    '${_commandes.where((c) => !['livree', 'annulee'].contains(c.statut)).length}',
                    Icons.local_shipping_outlined,
                    Colors.blue,
                  ),
                ]),
                const SizedBox(height: 24),

                // Accès rapide
                const Text('Navigation rapide', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                const SizedBox(height: 12),
                _NavTile(Icons.list_alt,         'Mes commandes',  '/commandes'),
                _NavTile(Icons.location_on_outlined, 'Mes adresses', '/adresses'),
                _NavTile(Icons.shopping_cart_outlined, 'Mon panier',  '/panier'),
                _NavTile(Icons.person_outline,    'Mon profil',    '/profil'),
                const SizedBox(height: 24),

                // Dernières commandes
                const Text('Dernières commandes', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                const SizedBox(height: 12),
                if (_commandes.isEmpty)
                  const Text('Aucune commande pour l\'instant.', style: TextStyle(color: Colors.grey))
                else
                  ..._commandes.take(3).map((c) => _CommandeRow(commande: c)),
              ],
            ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label, value;
  final IconData icon;
  final Color color;
  const _StatCard(this.label, this.value, this.icon, this.color);

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(children: [
            Icon(icon, color: color, size: 32),
            const SizedBox(width: 12),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(value, style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: color)),
              Text(label, style: const TextStyle(color: Colors.grey, fontSize: 12)),
            ]),
          ]),
        ),
      ),
    );
  }
}

class _NavTile extends StatelessWidget {
  final IconData icon;
  final String label, route;
  const _NavTile(this.icon, this.label, this.route);

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(icon, color: const Color(0xFF2E7D32)),
        title: Text(label),
        trailing: const Icon(Icons.arrow_forward_ios, size: 14, color: Colors.grey),
        onTap: () => Navigator.pushNamed(context, route),
      ),
    );
  }
}

class _CommandeRow extends StatelessWidget {
  final Commande commande;
  const _CommandeRow({required this.commande});

  @override
  Widget build(BuildContext context) {
    final color = Color(AppConstants.statutColors[commande.statut] ?? 0xFF9E9E9E);
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        title: Text(commande.numeroCommande, style: const TextStyle(fontWeight: FontWeight.w600, fontFamily: 'monospace')),
        subtitle: Text('${commande.producteur ?? ''} • ${commande.total ?? ''} HTG'),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: color.withOpacity(0.3)),
          ),
          child: Text(commande.statutLabel ?? commande.statut,
            style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w500)),
        ),
      ),
    );
  }
}
```

---

## 12. Acheteur — Mes Commandes

> Écran correspondant à `templates/dashboard/acheteur_commandes.html`

```dart
// lib/screens/dashboard/acheteur/commandes_screen.dart
import 'package:flutter/material.dart';
import '../../../services/api_service.dart';
import '../../../models/commande.dart';
import '../../../core/constants.dart';

class AcheteurCommandesScreen extends StatefulWidget {
  const AcheteurCommandesScreen({super.key});
  @override
  State<AcheteurCommandesScreen> createState() => _AcheteurCommandesScreenState();
}

class _AcheteurCommandesScreenState extends State<AcheteurCommandesScreen> {
  List<Commande> _commandes = [];
  bool _loading  = true;
  String? _filtre;

  final List<Map<String, String>> _filtres = [
    {'value': '',              'label': 'Toutes'},
    {'value': 'en_attente',    'label': 'En attente'},
    {'value': 'confirmee',     'label': 'Confirmées'},
    {'value': 'en_preparation','label': 'En préparation'},
    {'value': 'livree',        'label': 'Livrées'},
    {'value': 'annulee',       'label': 'Annulées'},
  ];

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final res = await ApiService.instance.getMesCommandes(statut: _filtre?.isEmpty == true ? null : _filtre);
      final list = (res.data as List).map((e) => Commande.fromJson(e as Map<String, dynamic>)).toList();
      setState(() { _commandes = list; _loading = false; });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mes Commandes'),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          // Filtres
          SizedBox(
            height: 50,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              children: _filtres.map((f) {
                final sel = _filtre == f['value'];
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: FilterChip(
                    label: Text(f['label']!),
                    selected: sel,
                    selectedColor: const Color(0xFF2E7D32),
                    labelStyle: TextStyle(color: sel ? Colors.white : null),
                    onSelected: (_) {
                      setState(() => _filtre = f['value']);
                      _load();
                    },
                  ),
                );
              }).toList(),
            ),
          ),

          // Liste
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _commandes.isEmpty
                    ? const Center(child: Text('Aucune commande trouvée.', style: TextStyle(color: Colors.grey)))
                    : RefreshIndicator(
                        onRefresh: _load,
                        child: ListView.separated(
                          padding: const EdgeInsets.all(12),
                          itemCount: _commandes.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 8),
                          itemBuilder: (_, i) => _CommandeCard(commande: _commandes[i]),
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}

class _CommandeCard extends StatelessWidget {
  final Commande commande;
  const _CommandeCard({required this.commande});

  @override
  Widget build(BuildContext context) {
    final color = Color(AppConstants.statutColors[commande.statut] ?? 0xFF9E9E9E);
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(commande.numeroCommande,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontFamily: 'monospace')),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: color.withOpacity(0.4)),
                  ),
                  child: Text(commande.statutLabel ?? commande.statut,
                    style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (commande.producteur != null) Text('Producteur : ${commande.producteur}'),
            Text('Total : ${commande.total ?? 'N/A'} HTG',
              style: const TextStyle(color: Color(0xFF2E7D32), fontWeight: FontWeight.bold)),
            Text('Paiement : ${commande.statutPaiement ?? 'N/A'}',
              style: const TextStyle(color: Colors.grey, fontSize: 12)),
          ],
        ),
      ),
    );
  }
}
```

---

## 13. Acheteur — Mes Adresses

> Écran correspondant à `templates/dashboard/acheteur_adresses.html`

```dart
// lib/screens/dashboard/acheteur/adresses_screen.dart
import 'package:flutter/material.dart';
import '../../../services/api_service.dart';
import '../../../models/adresse.dart';

class AdressesScreen extends StatefulWidget {
  const AdressesScreen({super.key});
  @override
  State<AdressesScreen> createState() => _AdressesScreenState();
}

class _AdressesScreenState extends State<AdressesScreen> {
  List<Adresse> _adresses = [];
  bool _loading = true;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final res = await ApiService.instance.getAdresses();
      final list = (res.data as List).map((e) => Adresse.fromJson(e as Map<String, dynamic>)).toList();
      setState(() { _adresses = list; _loading = false; });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  Future<void> _setDefault(int id) async {
    try {
      await ApiService.instance.setAdresseDefault(id);
      _load();
    } catch (_) {}
  }

  Future<void> _delete(int id) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Supprimer cette adresse ?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Annuler')),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Supprimer', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
    if (confirm == true) {
      await ApiService.instance.deleteAdresse(id);
      _load();
    }
  }

  void _openForm({Adresse? adresse}) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
      builder: (ctx) => _AdresseForm(
        adresse: adresse,
        onSaved: () { Navigator.pop(ctx); _load(); },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mes Adresses'),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openForm(),
        backgroundColor: const Color(0xFF2E7D32),
        label: const Text('Ajouter', style: TextStyle(color: Colors.white)),
        icon: const Icon(Icons.add, color: Colors.white),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _adresses.isEmpty
              ? const Center(child: Text('Aucune adresse enregistrée.'))
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: _adresses.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) {
                    final a = _adresses[i];
                    return Card(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: a.isDefault
                            ? const BorderSide(color: Color(0xFF2E7D32), width: 2)
                            : BorderSide.none,
                      ),
                      child: ListTile(
                        leading: Icon(
                          a.typeAdresse == 'livraison' ? Icons.home_outlined : Icons.receipt_outlined,
                          color: a.isDefault ? const Color(0xFF2E7D32) : Colors.grey,
                        ),
                        title: Text('${a.libelle ?? a.rue}${a.isDefault ? ' (défaut)' : ''}'),
                        subtitle: Text('${a.rue}, ${a.commune}, ${a.departement}'),
                        trailing: PopupMenuButton(
                          itemBuilder: (ctx) => [
                            if (!a.isDefault) PopupMenuItem(
                              onTap: () => _setDefault(a.id),
                              child: const Text('Définir par défaut'),
                            ),
                            PopupMenuItem(
                              onTap: () => _openForm(adresse: a),
                              child: const Text('Modifier'),
                            ),
                            PopupMenuItem(
                              onTap: () => _delete(a.id),
                              child: const Text('Supprimer', style: TextStyle(color: Colors.red)),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}

class _AdresseForm extends StatefulWidget {
  final Adresse? adresse;
  final VoidCallback onSaved;
  const _AdresseForm({this.adresse, required this.onSaved});
  @override
  State<_AdresseForm> createState() => _AdresseFormState();
}

class _AdresseFormState extends State<_AdresseForm> {
  final _rueCtrl     = TextEditingController();
  final _communeCtrl = TextEditingController();
  String _departement = 'ouest';
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    if (widget.adresse != null) {
      _rueCtrl.text     = widget.adresse!.rue;
      _communeCtrl.text = widget.adresse!.commune;
      _departement      = widget.adresse!.departement;
    }
  }

  Future<void> _save() async {
    setState(() => _loading = true);
    try {
      final data = {'rue': _rueCtrl.text.trim(), 'commune': _communeCtrl.text.trim(), 'departement': _departement, 'type_adresse': 'livraison'};
      if (widget.adresse != null) {
        await ApiService.instance.updateAdresse(widget.adresse!.id, data);
      } else {
        await ApiService.instance.createAdresse(data);
      }
      widget.onSaved();
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom, left: 20, right: 20, top: 20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(widget.adresse == null ? 'Nouvelle adresse' : 'Modifier l\'adresse',
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
          const SizedBox(height: 16),
          TextFormField(controller: _rueCtrl, decoration: const InputDecoration(labelText: 'Rue / Adresse', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextFormField(controller: _communeCtrl, decoration: const InputDecoration(labelText: 'Commune', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: _departement,
            decoration: const InputDecoration(labelText: 'Département', border: OutlineInputBorder()),
            items: const [
              DropdownMenuItem(value: 'ouest',      child: Text('Ouest')),
              DropdownMenuItem(value: 'nord',       child: Text('Nord')),
              DropdownMenuItem(value: 'sud',        child: Text('Sud')),
              DropdownMenuItem(value: 'artibonite', child: Text('Artibonite')),
              DropdownMenuItem(value: 'centre',     child: Text('Centre')),
              DropdownMenuItem(value: 'nord_est',   child: Text('Nord-Est')),
              DropdownMenuItem(value: 'nord_ouest', child: Text('Nord-Ouest')),
              DropdownMenuItem(value: 'sud_est',    child: Text('Sud-Est')),
              DropdownMenuItem(value: 'grand_anse', child: Text('Grand\'Anse')),
              DropdownMenuItem(value: 'nippes',     child: Text('Nippes')),
            ],
            onChanged: (v) => setState(() => _departement = v!),
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: _loading ? null : _save,
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2E7D32), padding: const EdgeInsets.symmetric(vertical: 14)),
            child: _loading
                ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                : Text(widget.adresse == null ? 'Enregistrer' : 'Mettre à jour', style: const TextStyle(color: Colors.white)),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}
```

---

## 14. Acheteur — Mon Profil

> Écran correspondant à `templates/dashboard/acheteur_profil.html`

```dart
// lib/screens/dashboard/acheteur/profil_screen.dart
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:dio/dio.dart';
import '../../../services/api_service.dart';
import '../../../models/user.dart';
import '../../../core/constants.dart';
import 'dart:io';

class AcheteurProfilScreen extends StatefulWidget {
  const AcheteurProfilScreen({super.key});
  @override
  State<AcheteurProfilScreen> createState() => _AcheteurProfilScreenState();
}

class _AcheteurProfilScreenState extends State<AcheteurProfilScreen> {
  User? _user;
  final _firstNameCtrl = TextEditingController();
  final _lastNameCtrl  = TextEditingController();
  final _telCtrl       = TextEditingController();
  bool _loading = false;
  File? _newPhoto;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final res = await ApiService.instance.getMe();
      final user = User.fromJson(res.data as Map<String, dynamic>);
      setState(() {
        _user          = user;
        _firstNameCtrl.text = user.firstName;
        _lastNameCtrl.text  = user.lastName;
        _telCtrl.text       = user.telephone ?? '';
      });
    } catch (_) {}
  }

  Future<void> _pickPhoto() async {
    final img = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 80);
    if (img != null) setState(() => _newPhoto = File(img.path));
  }

  Future<void> _save() async {
    setState(() => _loading = true);
    try {
      final formData = FormData.fromMap({
        'first_name': _firstNameCtrl.text.trim(),
        'last_name':  _lastNameCtrl.text.trim(),
        'telephone':  _telCtrl.text.trim(),
        if (_newPhoto != null)
          'photo': await MultipartFile.fromFile(_newPhoto!.path, filename: 'photo.jpg'),
      });
      await ApiService.instance.updateMe(formData);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profil mis à jour !'), backgroundColor: Color(0xFF2E7D32)),
      );
      _load();
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mon Profil'),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            // Avatar
            GestureDetector(
              onTap: _pickPhoto,
              child: Stack(
                children: [
                  CircleAvatar(
                    radius: 50,
                    backgroundImage: _newPhoto != null
                        ? FileImage(_newPhoto!) as ImageProvider
                        : (_user?.photoUrl != null
                            ? NetworkImage(imageUrl(_user!.photoUrl)) as ImageProvider
                            : null),
                    backgroundColor: const Color(0xFFE8F5E9),
                    child: _newPhoto == null && _user?.photoUrl == null
                        ? const Icon(Icons.person, size: 50, color: Color(0xFF2E7D32))
                        : null,
                  ),
                  Positioned(
                    bottom: 0, right: 0,
                    child: Container(
                      padding: const EdgeInsets.all(6),
                      decoration: const BoxDecoration(
                        color: Color(0xFF2E7D32),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.camera_alt, size: 16, color: Colors.white),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Formulaire
            Row(children: [
              Expanded(child: _field(_firstNameCtrl, 'Prénom')),
              const SizedBox(width: 12),
              Expanded(child: _field(_lastNameCtrl, 'Nom')),
            ]),
            const SizedBox(height: 16),
            _field(_telCtrl, 'Téléphone', type: TextInputType.phone),
            const SizedBox(height: 32),

            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _loading ? null : _save,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF2E7D32),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                child: _loading
                    ? const SizedBox(height: 18, width: 18,
                        child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : const Text('Enregistrer', style: TextStyle(color: Colors.white, fontSize: 16)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _field(TextEditingController ctrl, String label, {TextInputType type = TextInputType.text}) {
    return TextFormField(
      controller: ctrl,
      keyboardType: type,
      decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
    );
  }
}
```

---

## 15. Dashboard Producteur

> Écran correspondant à `templates/dashboard/producteur.html`

```dart
// lib/screens/dashboard/producteur/producteur_dashboard.dart
import 'package:flutter/material.dart';
import '../../../services/api_service.dart';
import '../../../models/producteur_profil.dart';

class ProducteurDashboard extends StatefulWidget {
  const ProducteurDashboard({super.key});
  @override
  State<ProducteurDashboard> createState() => _ProducteurDashboardState();
}

class _ProducteurDashboardState extends State<ProducteurDashboard> {
  ProducteurStats? _stats;
  bool _loading = true;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final res = await ApiService.instance.getProducteurStats();
      setState(() {
        _stats = ProducteurStats.fromJson(res.data as Map<String, dynamic>);
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7F2),
      appBar: AppBar(
        title: const Text('Mon Tableau de Bord'),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // Statistiques
                  if (_stats != null) ...[
                    const Text('Statistiques', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const SizedBox(height: 12),
                    GridView.count(
                      crossAxisCount: 2,
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      mainAxisSpacing: 12,
                      crossAxisSpacing: 12,
                      childAspectRatio: 1.5,
                      children: [
                        _StatTile('Commandes totales', '${_stats!.nbCommandesTotal}', Icons.shopping_bag_outlined, Colors.blue),
                        _StatTile('En attente', '${_stats!.nbCommandesAttente}', Icons.hourglass_empty, Colors.orange),
                        _StatTile('Produits actifs', '${_stats!.nbProduitsActifs}', Icons.inventory_2_outlined, const Color(0xFF2E7D32)),
                        _StatTile('Chiffre d\'affaires', '${_stats!.chiffreAffaires} HTG', Icons.trending_up, Colors.purple),
                      ],
                    ),
                    const SizedBox(height: 24),
                  ],

                  // Navigation
                  const Text('Gestion', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 12),
                  _NavCard(Icons.list_alt,         'Commandes reçues',  '/producteur/commandes',  'Gérer vos commandes entrantes'),
                  _NavCard(Icons.store_outlined,   'Mon catalogue',     '/producteur/catalogue',  'Ajouter et gérer vos produits'),
                  _NavCard(Icons.local_shipping_outlined, 'Mes collectes', '/producteur/collectes', 'Voir les collectes planifiées'),
                  _NavCard(Icons.bar_chart,        'Rapports',          '/producteur/rapport',    'Statistiques de ventes'),
                  _NavCard(Icons.person_outline,   'Mon profil',        '/producteur/profil',     'Modifier mes informations'),
                ],
              ),
            ),
    );
  }
}

class _StatTile extends StatelessWidget {
  final String label, value;
  final IconData icon;
  final Color color;
  const _StatTile(this.label, this.value, this.icon, this.color);

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 4),
            Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color)),
            Text(label, style: const TextStyle(color: Colors.grey, fontSize: 11), maxLines: 2, overflow: TextOverflow.ellipsis),
          ],
        ),
      ),
    );
  }
}

class _NavCard extends StatelessWidget {
  final IconData icon;
  final String label, route, subtitle;
  const _NavCard(this.icon, this.label, this.route, this.subtitle);

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: const Color(0xFFE8F5E9),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: const Color(0xFF2E7D32)),
        ),
        title: Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(subtitle, style: const TextStyle(fontSize: 12)),
        trailing: const Icon(Icons.arrow_forward_ios, size: 14, color: Colors.grey),
        onTap: () => Navigator.pushNamed(context, route),
      ),
    );
  }
}
```

---

## 16. Producteur — Commandes reçues

> Écran correspondant à `templates/dashboard/producteur_commandes.html`

```dart
// lib/screens/dashboard/producteur/prod_commandes_screen.dart
import 'package:flutter/material.dart';
import '../../../services/api_service.dart';
import '../../../models/commande.dart';
import '../../../core/constants.dart';

class ProdCommandesScreen extends StatefulWidget {
  const ProdCommandesScreen({super.key});
  @override
  State<ProdCommandesScreen> createState() => _ProdCommandesScreenState();
}

class _ProdCommandesScreenState extends State<ProdCommandesScreen> {
  List<Commande> _commandes = [];
  bool _loading = true;
  String? _filtre;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final res = await ApiService.instance.getCommandesProducteur(statut: _filtre?.isEmpty == true ? null : _filtre);
      final list = (res.data as List).map((e) => Commande.fromJson(e as Map<String, dynamic>)).toList();
      setState(() { _commandes = list; _loading = false; });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  void _openDetail(Commande c) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => _CommandeDetailSheet(commande: c, onAction: (action, motif) async {
        await ApiService.instance.changerStatutCommande(c.numeroCommande, action, motif: motif);
        Navigator.pop(ctx);
        _load();
      }),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Commandes Reçues'),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          // Filtres statut
          SizedBox(
            height: 50,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              children: [
                for (final f in [
                  {'v': '',              'l': 'Toutes'},
                  {'v': 'en_attente',    'l': 'En attente'},
                  {'v': 'confirmee',     'l': 'Confirmées'},
                  {'v': 'en_preparation','l': 'En préparation'},
                  {'v': 'prete',         'l': 'Prêtes'},
                  {'v': 'livree',        'l': 'Livrées'},
                ]) Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: FilterChip(
                    label: Text(f['l']!),
                    selected: _filtre == f['v'],
                    selectedColor: const Color(0xFF2E7D32),
                    labelStyle: TextStyle(color: _filtre == f['v'] ? Colors.white : null),
                    onSelected: (_) { setState(() => _filtre = f['v']); _load(); },
                  ),
                ),
              ],
            ),
          ),

          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _commandes.isEmpty
                    ? const Center(child: Text('Aucune commande.', style: TextStyle(color: Colors.grey)))
                    : RefreshIndicator(
                        onRefresh: _load,
                        child: ListView.separated(
                          padding: const EdgeInsets.all(12),
                          itemCount: _commandes.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 8),
                          itemBuilder: (_, i) {
                            final c = _commandes[i];
                            final color = Color(AppConstants.statutColors[c.statut] ?? 0xFF9E9E9E);
                            return Card(
                              child: ListTile(
                                title: Text(c.numeroCommande,
                                  style: const TextStyle(fontWeight: FontWeight.bold, fontFamily: 'monospace')),
                                subtitle: Text('${c.acheteur ?? ''} • ${c.total ?? ''} HTG'),
                                trailing: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: color.withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: Text(c.statutLabel ?? c.statut,
                                    style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
                                ),
                                onTap: () => _openDetail(c),
                              ),
                            );
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}

class _CommandeDetailSheet extends StatelessWidget {
  final Commande commande;
  final Future<void> Function(String action, String? motif) onAction;

  const _CommandeDetailSheet({required this.commande, required this.onAction});

  @override
  Widget build(BuildContext context) {
    final actions = <Map<String, String>>{};
    switch (commande.statut) {
      case 'en_attente':    actions.addAll({'action': 'confirmer',   'label': 'Confirmer'}); break;
      case 'confirmee':     actions.addAll({'action': 'preparer',    'label': 'Démarrer préparation'}); break;
      case 'en_preparation':actions.addAll({'action': 'prete',       'label': 'Marquer Prête'}); break;
    }

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(commande.numeroCommande, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18, fontFamily: 'monospace')),
          const SizedBox(height: 16),
          _InfoRow('Acheteur', commande.acheteur ?? '-'),
          _InfoRow('Total', '${commande.total ?? '-'} HTG'),
          _InfoRow('Livraison', commande.modeLivraison ?? '-'),
          _InfoRow('Paiement', commande.methodePaiement ?? '-'),
          if (commande.notesAcheteur?.isNotEmpty == true)
            _InfoRow('Notes', commande.notesAcheteur!),
          const SizedBox(height: 20),
          if (actions.isNotEmpty)
            Row(children: [
              Expanded(
                child: ElevatedButton(
                  onPressed: () => onAction(actions['action']!, null),
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2E7D32)),
                  child: Text(actions['label']!, style: const TextStyle(color: Colors.white)),
                ),
              ),
              const SizedBox(width: 12),
              if (commande.estAnnulable)
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => onAction('annuler', 'Rupture de stock'),
                    style: OutlinedButton.styleFrom(side: const BorderSide(color: Colors.red)),
                    child: const Text('Annuler', style: TextStyle(color: Colors.red)),
                  ),
                ),
            ]),
          const SizedBox(height: 8),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label, value;
  const _InfoRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 90, child: Text('$label :', style: const TextStyle(color: Colors.grey, fontSize: 13))),
          Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w500))),
        ],
      ),
    );
  }
}
```

---

## 17. Producteur — Mon Catalogue

> Écran correspondant à `templates/dashboard/producteur_catalogue.html`

```dart
// lib/screens/dashboard/producteur/prod_catalogue_screen.dart
import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import '../../../services/api_service.dart';
import '../../../models/produit.dart';
import '../../../core/constants.dart';
import 'package:cached_network_image/cached_network_image.dart';

class ProdCatalogueScreen extends StatefulWidget {
  const ProdCatalogueScreen({super.key});
  @override
  State<ProdCatalogueScreen> createState() => _ProdCatalogueScreenState();
}

class _ProdCatalogueScreenState extends State<ProdCatalogueScreen> {
  List<Produit> _produits = [];
  bool _loading = true;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final res = await ApiService.instance.getMesProduits();
      final page = CataloguePage.fromJson(res.data as Map<String, dynamic>);
      setState(() { _produits = page.results; _loading = false; });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  void _openForm({Produit? produit}) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => _ProduitForm(
        produit: produit,
        onSaved: () { Navigator.pop(ctx); _load(); },
      ),
    );
  }

  Future<void> _delete(Produit p) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Supprimer ce produit ?'),
        content: Text('Voulez-vous vraiment supprimer "${p.nom}" ?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Annuler')),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Supprimer', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
    if (confirm == true) {
      await ApiService.instance.deleteProduit(p.slug);
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mon Catalogue'),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openForm(),
        backgroundColor: const Color(0xFF2E7D32),
        label: const Text('Nouveau produit', style: TextStyle(color: Colors.white)),
        icon: const Icon(Icons.add, color: Colors.white),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _produits.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.inventory_2_outlined, size: 64, color: Colors.grey),
                      const SizedBox(height: 16),
                      const Text('Aucun produit dans votre catalogue.', style: TextStyle(color: Colors.grey)),
                      const SizedBox(height: 24),
                      ElevatedButton.icon(
                        onPressed: () => _openForm(),
                        icon: const Icon(Icons.add),
                        label: const Text('Ajouter un produit'),
                        style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2E7D32), foregroundColor: Colors.white),
                      ),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 80),
                    itemCount: _produits.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) {
                      final p = _produits[i];
                      return Card(
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        child: ListTile(
                          leading: ClipRRect(
                            borderRadius: BorderRadius.circular(8),
                            child: SizedBox(
                              width: 56, height: 56,
                              child: CachedNetworkImage(
                                imageUrl: imageUrl(p.imagePrincipale),
                                fit: BoxFit.cover,
                                errorWidget: (_, __, ___) => Container(
                                  color: const Color(0xFFE8F5E9),
                                  child: const Icon(Icons.agriculture, color: Colors.green),
                                ),
                              ),
                            ),
                          ),
                          title: Text(p.nom, style: const TextStyle(fontWeight: FontWeight.w600)),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('${p.prixUnitaire} HTG / ${p.uniteVenteLabel ?? p.uniteVente}',
                                style: const TextStyle(color: Color(0xFF2E7D32))),
                              Text('Stock : ${p.stockDisponible} ${p.uniteVente}',
                                style: const TextStyle(color: Colors.grey, fontSize: 12)),
                            ],
                          ),
                          trailing: PopupMenuButton(
                            itemBuilder: (ctx) => [
                              PopupMenuItem(onTap: () => _openForm(produit: p), child: const Text('Modifier')),
                              PopupMenuItem(onTap: () => _delete(p), child: const Text('Supprimer', style: TextStyle(color: Colors.red))),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}

class _ProduitForm extends StatefulWidget {
  final Produit? produit;
  final VoidCallback onSaved;
  const _ProduitForm({this.produit, required this.onSaved});
  @override
  State<_ProduitForm> createState() => _ProduitFormState();
}

class _ProduitFormState extends State<_ProduitForm> {
  final _nomCtrl   = TextEditingController();
  final _prixCtrl  = TextEditingController();
  final _stockCtrl = TextEditingController();
  final _descCtrl  = TextEditingController();
  String _unite    = 'kg';
  File? _image;
  bool _loading    = false;

  final List<Map<String, String>> _unites = [
    {'v': 'kg',     'l': 'Kilogramme'},
    {'v': 'tonne',  'l': 'Tonne'},
    {'v': 'sac_50', 'l': 'Sac 50kg'},
    {'v': 'sac_25', 'l': 'Sac 25kg'},
    {'v': 'botte',  'l': 'Botte'},
    {'v': 'piece',  'l': 'Pièce'},
    {'v': 'litre',  'l': 'Litre'},
    {'v': 'carton', 'l': 'Carton'},
  ];

  @override
  void initState() {
    super.initState();
    if (widget.produit != null) {
      final p = widget.produit!;
      _nomCtrl.text   = p.nom;
      _prixCtrl.text  = p.prixUnitaire;
      _stockCtrl.text = '${p.stockDisponible}';
      _descCtrl.text  = p.description ?? '';
      _unite          = p.uniteVente;
    }
  }

  Future<void> _pickImage() async {
    final img = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 80);
    if (img != null) setState(() => _image = File(img.path));
  }

  Future<void> _save() async {
    setState(() => _loading = true);
    try {
      final formData = FormData.fromMap({
        'nom':               _nomCtrl.text.trim(),
        'prix_unitaire':     _prixCtrl.text.trim(),
        'stock_disponible':  _stockCtrl.text.trim(),
        'unite_vente':       _unite,
        'description':       _descCtrl.text.trim(),
        if (_image != null)
          'image_principale': await MultipartFile.fromFile(_image!.path, filename: 'produit.jpg'),
      });

      if (widget.produit != null) {
        await ApiService.instance.updateProduit(widget.produit!.slug, formData);
      } else {
        await ApiService.instance.createProduit(formData);
      }
      widget.onSaved();
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
        left: 20, right: 20, top: 24,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(widget.produit == null ? 'Nouveau produit' : 'Modifier le produit',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            const SizedBox(height: 16),

            // Photo
            GestureDetector(
              onTap: _pickImage,
              child: Container(
                height: 120,
                decoration: BoxDecoration(
                  color: const Color(0xFFE8F5E9),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFF2E7D32).withOpacity(0.3)),
                ),
                child: _image != null
                    ? ClipRRect(borderRadius: BorderRadius.circular(12), child: Image.file(_image!, fit: BoxFit.cover))
                    : const Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                        Icon(Icons.add_photo_alternate_outlined, size: 36, color: Color(0xFF2E7D32)),
                        Text('Ajouter une photo', style: TextStyle(color: Color(0xFF2E7D32))),
                      ]),
              ),
            ),
            const SizedBox(height: 12),

            TextFormField(controller: _nomCtrl,   decoration: const InputDecoration(labelText: 'Nom du produit *', border: OutlineInputBorder())),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(child: TextFormField(controller: _prixCtrl, keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Prix (HTG) *', border: OutlineInputBorder(), suffixText: 'HTG'))),
              const SizedBox(width: 12),
              Expanded(child: TextFormField(controller: _stockCtrl, keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Stock *', border: OutlineInputBorder()))),
            ]),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _unite,
              decoration: const InputDecoration(labelText: 'Unité de vente', border: OutlineInputBorder()),
              items: _unites.map((u) => DropdownMenuItem(value: u['v'], child: Text(u['l']!))).toList(),
              onChanged: (v) => setState(() => _unite = v!),
            ),
            const SizedBox(height: 12),
            TextFormField(controller: _descCtrl, maxLines: 2,
              decoration: const InputDecoration(labelText: 'Description', border: OutlineInputBorder())),
            const SizedBox(height: 20),

            ElevatedButton(
              onPressed: _loading ? null : _save,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF2E7D32),
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              child: _loading
                  ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : Text(widget.produit == null ? 'Créer le produit' : 'Enregistrer', style: const TextStyle(color: Colors.white, fontSize: 16)),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}
```

---

## 18. Producteur — Mes Collectes

> Écran correspondant à `templates/dashboard/producteur_collectes.html`

```dart
// lib/screens/dashboard/producteur/prod_collectes_screen.dart
import 'package:flutter/material.dart';
import '../../../services/api_service.dart';

class ProdCollectesScreen extends StatefulWidget {
  const ProdCollectesScreen({super.key});
  @override
  State<ProdCollectesScreen> createState() => _ProdCollectesScreenState();
}

class _ProdCollectesScreenState extends State<ProdCollectesScreen> {
  List<dynamic> _participations = [];
  bool _loading = true;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final res = await ApiService.instance.getMesParticipations();
      setState(() {
        _participations = res.data is List ? res.data as List : (res.data['results'] as List? ?? []);
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  Future<void> _confirmer(int id) async {
    try {
      await ApiService.instance.confirmerParticipation(id);
      _load();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Participation confirmée !'), backgroundColor: Color(0xFF2E7D32)),
      );
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mes Collectes'),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _participations.isEmpty
              ? const Center(child: Text('Aucune participation à une collecte.', style: TextStyle(color: Colors.grey)))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(12),
                    itemCount: _participations.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) {
                      final p = _participations[i] as Map<String, dynamic>;
                      final collecte = p['collecte'] as Map<String, dynamic>? ?? {};
                      final statut = p['statut'] as String? ?? '';

                      return Card(
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(collecte['reference'] as String? ?? 'Collecte',
                                    style: const TextStyle(fontWeight: FontWeight.bold, fontFamily: 'monospace')),
                                  _StatutBadge(statut),
                                ],
                              ),
                              const SizedBox(height: 8),
                              if (collecte['date_planifiee'] != null)
                                Row(children: [
                                  const Icon(Icons.calendar_today, size: 14, color: Colors.grey),
                                  const SizedBox(width: 4),
                                  Text('Date : ${collecte['date_planifiee']}', style: const TextStyle(color: Colors.grey, fontSize: 13)),
                                ]),
                              if (collecte['zone'] != null)
                                Row(children: [
                                  const Icon(Icons.location_on_outlined, size: 14, color: Colors.grey),
                                  const SizedBox(width: 4),
                                  Text('Zone : ${(collecte['zone'] as Map?)?['nom'] ?? ''}',
                                    style: const TextStyle(color: Colors.grey, fontSize: 13)),
                                ]),
                              if (p['quantite_prevue'] != null) ...[
                                const SizedBox(height: 4),
                                Text('Qté prévue : ${p['quantite_prevue']}  |  Collectée : ${p['quantite_collectee'] ?? 0}',
                                  style: const TextStyle(fontSize: 12)),
                              ],
                              if (statut == 'inscrit') ...[
                                const SizedBox(height: 12),
                                SizedBox(
                                  width: double.infinity,
                                  child: ElevatedButton(
                                    onPressed: () => _confirmer(p['id'] as int),
                                    style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2E7D32)),
                                    child: const Text('Confirmer ma participation', style: TextStyle(color: Colors.white)),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}

class _StatutBadge extends StatelessWidget {
  final String statut;
  const _StatutBadge(this.statut);

  @override
  Widget build(BuildContext context) {
    final colors = {
      'inscrit': Colors.blue,
      'confirme': const Color(0xFF2E7D32),
      'present': Colors.green,
      'absent': Colors.red,
      'annule': Colors.grey,
    };
    final color = colors[statut] ?? Colors.grey;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Text(statut, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }
}
```

---

## 19. Producteur — Mon Profil

> Écran correspondant à `templates/dashboard/producteur_profil.html`

```dart
// lib/screens/dashboard/producteur/prod_profil_screen.dart
import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import '../../../services/api_service.dart';
import '../../../models/producteur_profil.dart';
import '../../../core/constants.dart';
import 'package:cached_network_image/cached_network_image.dart';

class ProdProfilScreen extends StatefulWidget {
  const ProdProfilScreen({super.key});
  @override
  State<ProdProfilScreen> createState() => _ProdProfilScreenState();
}

class _ProdProfilScreenState extends State<ProdProfilScreen> {
  ProducteurProfil? _profil;
  final _descCtrl      = TextEditingController();
  final _superficieCtrl = TextEditingController();
  final _telCtrl       = TextEditingController();
  bool _loading  = false;
  bool _saving   = false;
  File? _newPhoto;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final res = await ApiService.instance.getProducteurProfil();
      final profil = ProducteurProfil.fromJson(res.data as Map<String, dynamic>);
      setState(() {
        _profil = profil;
        _descCtrl.text       = profil.description ?? '';
        _superficieCtrl.text = profil.superficieHa ?? '';
        _telCtrl.text        = profil.telephone ?? '';
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      final formData = FormData.fromMap({
        'description':  _descCtrl.text.trim(),
        'superficie_ha':_superficieCtrl.text.trim(),
        'telephone':    _telCtrl.text.trim(),
        if (_newPhoto != null)
          'photo': await MultipartFile.fromFile(_newPhoto!.path, filename: 'photo.jpg'),
      });
      await ApiService.instance.updateProducteurProfil(formData);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profil mis à jour !'), backgroundColor: Color(0xFF2E7D32)),
      );
      _load();
    } catch (_) {
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    if (_profil == null) return const Scaffold(body: Center(child: Text('Profil introuvable')));

    final p = _profil!;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Mon Profil Producteur'),
        backgroundColor: const Color(0xFF2E7D32),
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header avec photo + code
            Row(
              children: [
                GestureDetector(
                  onTap: () async {
                    final img = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 80);
                    if (img != null) setState(() => _newPhoto = File(img.path));
                  },
                  child: Stack(children: [
                    CircleAvatar(
                      radius: 40,
                      backgroundImage: _newPhoto != null
                          ? FileImage(_newPhoto!) as ImageProvider
                          : (p.photo != null ? NetworkImage(imageUrl(p.photo)) as ImageProvider : null),
                      backgroundColor: const Color(0xFFE8F5E9),
                      child: p.photo == null && _newPhoto == null
                          ? const Icon(Icons.agriculture, size: 36, color: Color(0xFF2E7D32))
                          : null,
                    ),
                    Positioned(bottom: 0, right: 0,
                      child: Container(
                        padding: const EdgeInsets.all(4),
                        decoration: const BoxDecoration(color: Color(0xFF2E7D32), shape: BoxShape.circle),
                        child: const Icon(Icons.camera_alt, size: 12, color: Colors.white),
                      ),
                    ),
                  ]),
                ),
                const SizedBox(width: 16),
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(p.nomComplet, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                  Text(p.codeProducteur, style: const TextStyle(fontFamily: 'monospace', color: Colors.grey)),
                  Container(
                    margin: const EdgeInsets.only(top: 4),
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: p.statut == 'actif' ? Colors.green.shade50 : Colors.orange.shade50,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: p.statut == 'actif' ? Colors.green.shade200 : Colors.orange.shade200),
                    ),
                    child: Text(p.statutLabel ?? p.statut,
                      style: TextStyle(
                        color: p.statut == 'actif' ? Colors.green.shade700 : Colors.orange.shade700,
                        fontSize: 12, fontWeight: FontWeight.w500,
                      )),
                  ),
                ]),
              ],
            ),
            const SizedBox(height: 24),

            // Infos fixes (lecture seule)
            const Text('Localisation', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 8),
            _InfoRow('Département', p.departementLabel ?? p.departement),
            _InfoRow('Commune', p.commune),
            if (p.localite != null) _InfoRow('Localité', p.localite!),
            const SizedBox(height: 20),
            const Divider(),
            const SizedBox(height: 20),

            // Champs modifiables
            const Text('Informations modifiables', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 12),
            TextFormField(
              controller: _telCtrl,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Téléphone', border: OutlineInputBorder(), prefixIcon: Icon(Icons.phone)),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _superficieCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Superficie (ha)', border: OutlineInputBorder(), suffixText: 'ha'),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _descCtrl,
              maxLines: 4,
              decoration: const InputDecoration(labelText: 'Description de votre exploitation', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 24),

            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _saving ? null : _save,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF2E7D32),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                child: _saving
                    ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : const Text('Enregistrer les modifications', style: TextStyle(color: Colors.white, fontSize: 16)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label, value;
  const _InfoRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(children: [
        SizedBox(width: 100, child: Text('$label :', style: const TextStyle(color: Colors.grey))),
        Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w500))),
      ]),
    );
  }
}
```

---

## 20. Producteur — En Attente de Validation

> Écran correspondant à `templates/dashboard/producteur_en_attente.html`

```dart
// lib/screens/dashboard/producteur/en_attente_screen.dart
import 'package:flutter/material.dart';
import '../../../services/api_service.dart';
import '../../../models/producteur_profil.dart';

class ProducteurEnAttenteScreen extends StatefulWidget {
  const ProducteurEnAttenteScreen({super.key});
  @override
  State<ProducteurEnAttenteScreen> createState() => _ProducteurEnAttenteScreenState();
}

class _ProducteurEnAttenteScreenState extends State<ProducteurEnAttenteScreen> {
  bool _checkingStatus = false;

  Future<void> _verifierStatut() async {
    setState(() => _checkingStatus = true);
    try {
      final res = await ApiService.instance.getProducteurProfil();
      final profil = ProducteurProfil.fromJson(res.data as Map<String, dynamic>);
      if (!mounted) return;

      if (profil.statut == 'actif') {
        Navigator.pushReplacementNamed(context, '/producteur');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Votre compte est toujours en attente de validation.'),
            backgroundColor: Colors.orange,
          ),
        );
      }
    } catch (_) {
    } finally {
      if (mounted) setState(() => _checkingStatus = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7F2),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // Illustration
              Container(
                width: 120,
                height: 120,
                decoration: BoxDecoration(
                  color: Colors.orange.shade100,
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.hourglass_empty, size: 64, color: Colors.orange),
              ),
              const SizedBox(height: 32),

              const Text(
                'Compte en attente de validation',
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              const Text(
                'Votre inscription a bien été reçue. Notre équipe est en train de vérifier vos informations.\n\n'
                'Vous recevrez une notification dès que votre compte sera activé.',
                style: TextStyle(color: Colors.grey, height: 1.6, fontSize: 15),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 40),

              // Étapes
              _Step(1, 'Inscription soumise', true),
              _Step(2, 'Vérification en cours', true),
              _Step(3, 'Activation du compte', false),
              const SizedBox(height: 40),

              // Bouton vérifier
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _checkingStatus ? null : _verifierStatut,
                  icon: _checkingStatus
                      ? const SizedBox(width: 18, height: 18,
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Icon(Icons.refresh),
                  label: const Text('Vérifier l\'état de mon compte'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF2E7D32),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                ),
              ),
              const SizedBox(height: 12),

              TextButton(
                onPressed: () => Navigator.pushReplacementNamed(context, '/login'),
                child: const Text('Se connecter avec un autre compte'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Step extends StatelessWidget {
  final int num;
  final String label;
  final bool done;
  const _Step(this.num, this.label, this.done);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(children: [
        Container(
          width: 32, height: 32,
          decoration: BoxDecoration(
            color: done ? const Color(0xFF2E7D32) : Colors.grey.shade200,
            shape: BoxShape.circle,
          ),
          child: Center(
            child: done
                ? const Icon(Icons.check, size: 18, color: Colors.white)
                : Text('$num', style: TextStyle(color: Colors.grey.shade600, fontWeight: FontWeight.bold)),
          ),
        ),
        const SizedBox(width: 12),
        Text(label, style: TextStyle(
          color: done ? const Color(0xFF2E7D32) : Colors.grey,
          fontWeight: done ? FontWeight.w600 : FontWeight.normal,
        )),
      ]),
    );
  }
}
```

---

## 21. Widget — Sélecteur Géographique

> Utilisé dans le formulaire d'inscription et adresses

```dart
// lib/screens/widgets/geo_selector.dart
import 'package:flutter/material.dart';
import '../../services/api_service.dart';

class GeoSelector extends StatefulWidget {
  final void Function({required String dept, required String commune, String? section}) onChanged;
  final String? initialDept;
  final String? initialCommune;

  const GeoSelector({
    super.key,
    required this.onChanged,
    this.initialDept,
    this.initialCommune,
  });

  @override
  State<GeoSelector> createState() => _GeoSelectorState();
}

class _GeoSelectorState extends State<GeoSelector> {
  List<Map<String, dynamic>> _departements = [];
  List<Map<String, dynamic>> _communes     = [];
  List<Map<String, dynamic>> _sections     = [];

  String? _dept;
  String? _commune;
  String? _section;

  bool _loadingDepts    = true;
  bool _loadingCommunes = false;
  bool _loadingSections = false;

  @override
  void initState() {
    super.initState();
    _loadDepts();
  }

  Future<void> _loadDepts() async {
    try {
      final res = await ApiService.instance.getDepartements();
      setState(() {
        _departements = (res.data as List).cast<Map<String, dynamic>>();
        _loadingDepts = false;
        if (widget.initialDept != null) {
          _dept = widget.initialDept;
          _loadCommunes(widget.initialDept!);
        }
      });
    } catch (_) {
      setState(() => _loadingDepts = false);
    }
  }

  Future<void> _loadCommunes(String deptSlug) async {
    setState(() { _loadingCommunes = true; _communes = []; _commune = null; _sections = []; _section = null; });
    try {
      final res = await ApiService.instance.getCommunes(deptSlug);
      setState(() {
        _communes     = (res.data as List).cast<Map<String, dynamic>>();
        _loadingCommunes = false;
        if (widget.initialCommune != null) _commune = widget.initialCommune;
      });
    } catch (_) {
      setState(() => _loadingCommunes = false);
    }
  }

  Future<void> _loadSections(String commune) async {
    if (_dept == null) return;
    setState(() { _loadingSections = true; _sections = []; _section = null; });
    try {
      final res = await ApiService.instance.getSections(_dept!, commune);
      setState(() {
        _sections     = (res.data as List).cast<Map<String, dynamic>>();
        _loadingSections = false;
      });
    } catch (_) {
      setState(() => _loadingSections = false);
    }
  }

  void _notify() {
    if (_dept != null && _commune != null) {
      widget.onChanged(dept: _dept!, commune: _commune!, section: _section);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Département
        _loadingDepts
            ? const LinearProgressIndicator()
            : DropdownButtonFormField<String>(
                value: _dept,
                decoration: const InputDecoration(labelText: 'Département *', border: OutlineInputBorder()),
                hint: const Text('Sélectionner...'),
                items: _departements.map((d) => DropdownMenuItem<String>(
                  value: d['slug'] as String? ?? d['value'] as String?,
                  child: Text(d['nom'] as String? ?? d['label'] as String? ?? ''),
                )).toList(),
                validator: (v) => v == null ? 'Requis' : null,
                onChanged: (v) {
                  if (v == null) return;
                  setState(() { _dept = v; _commune = null; _section = null; });
                  _loadCommunes(v);
                  _notify();
                },
              ),

        // Commune
        if (_dept != null) ...[
          const SizedBox(height: 12),
          _loadingCommunes
              ? const LinearProgressIndicator()
              : DropdownButtonFormField<String>(
                  value: _commune,
                  decoration: const InputDecoration(labelText: 'Commune *', border: OutlineInputBorder()),
                  hint: const Text('Sélectionner...'),
                  items: _communes.map((c) => DropdownMenuItem<String>(
                    value: c['nom'] as String? ?? c['value'] as String?,
                    child: Text(c['nom'] as String? ?? c['label'] as String? ?? ''),
                  )).toList(),
                  validator: (v) => v == null ? 'Requis' : null,
                  onChanged: (v) {
                    if (v == null) return;
                    setState(() { _commune = v; _section = null; });
                    _loadSections(v);
                    _notify();
                  },
                ),
        ],

        // Section communale (optionnel)
        if (_commune != null && _sections.isNotEmpty) ...[
          const SizedBox(height: 12),
          _loadingSections
              ? const LinearProgressIndicator()
              : DropdownButtonFormField<String>(
                  value: _section,
                  decoration: const InputDecoration(labelText: 'Section communale', border: OutlineInputBorder()),
                  hint: const Text('Optionnel'),
                  items: [
                    const DropdownMenuItem(value: null, child: Text('(Aucune)')),
                    ..._sections.map((s) => DropdownMenuItem<String>(
                      value: s['nom'] as String? ?? s['value'] as String?,
                      child: Text(s['nom'] as String? ?? s['label'] as String? ?? ''),
                    )),
                  ],
                  onChanged: (v) {
                    setState(() => _section = v);
                    _notify();
                  },
                ),
        ],
      ],
    );
  }
}
```

---

## 22. Navigation et Routing

### `lib/router.dart`

```dart
import 'package:go_router/go_router.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:convert';
import 'screens/auth/login_screen.dart';
import 'screens/auth/register_screen.dart';
import 'screens/catalogue/catalogue_screen.dart';
import 'screens/catalogue/produit_detail_screen.dart';
import 'screens/orders/panier_screen.dart';
import 'screens/orders/checkout_screen.dart';
import 'screens/dashboard/acheteur/acheteur_dashboard.dart';
import 'screens/dashboard/acheteur/commandes_screen.dart';
import 'screens/dashboard/acheteur/adresses_screen.dart';
import 'screens/dashboard/acheteur/profil_screen.dart';
import 'screens/dashboard/producteur/producteur_dashboard.dart';
import 'screens/dashboard/producteur/prod_commandes_screen.dart';
import 'screens/dashboard/producteur/prod_catalogue_screen.dart';
import 'screens/dashboard/producteur/prod_collectes_screen.dart';
import 'screens/dashboard/producteur/prod_profil_screen.dart';
import 'screens/dashboard/producteur/en_attente_screen.dart';
import 'models/user.dart';
import 'core/constants.dart';

final router = GoRouter(
  initialLocation: '/',
  redirect: (context, state) async {
    const storage = FlutterSecureStorage();
    final userJson = await storage.read(key: AppConstants.keyUser);
    final isLoggedIn = userJson != null;

    // Routes protégées nécessitant une connexion
    final protectedRoutes = [
      '/producteur',
      '/commandes',
      '/adresses',
      '/profil',
      '/checkout',
      '/panier',
    ];
    final isProtected = protectedRoutes.any((r) => state.matchedLocation.startsWith(r));

    if (!isLoggedIn && isProtected) return '/login';
    if (isLoggedIn && state.matchedLocation == '/login') {
      final user = User.fromJson(jsonDecode(userJson!) as Map<String, dynamic>);
      if (user.isSuperAdmin) return '/admin';
      if (user.isProducteur) return user.isProducteurActif ? '/producteur' : '/producteur/en-attente';
      return '/';
    }
    return null;
  },
  routes: [
    // Public
    GoRoute(path: '/',           builder: (_, __) => const CatalogueScreen()),
    GoRoute(path: '/login',      builder: (_, __) => const LoginScreen()),
    GoRoute(path: '/inscription', builder: (_, __) => const RegisterScreen()),
    GoRoute(
      path: '/produit/:slug',
      builder: (_, state) => ProduitDetailScreen(slug: state.pathParameters['slug']!),
    ),
    GoRoute(path: '/panier',    builder: (_, __) => const PanierScreen()),
    GoRoute(path: '/checkout',  builder: (_, __) => const CheckoutScreen()),

    // Acheteur
    GoRoute(path: '/dashboard',  builder: (_, __) => const AcheteurDashboard()),
    GoRoute(path: '/commandes',  builder: (_, __) => const AcheteurCommandesScreen()),
    GoRoute(path: '/adresses',   builder: (_, __) => const AdressesScreen()),
    GoRoute(path: '/profil',     builder: (_, __) => const AcheteurProfilScreen()),

    // Producteur
    GoRoute(path: '/producteur',              builder: (_, __) => const ProducteurDashboard()),
    GoRoute(path: '/producteur/commandes',    builder: (_, __) => const ProdCommandesScreen()),
    GoRoute(path: '/producteur/catalogue',    builder: (_, __) => const ProdCatalogueScreen()),
    GoRoute(path: '/producteur/collectes',    builder: (_, __) => const ProdCollectesScreen()),
    GoRoute(path: '/producteur/profil',       builder: (_, __) => const ProdProfilScreen()),
    GoRoute(path: '/producteur/en-attente',   builder: (_, __) => const ProducteurEnAttenteScreen()),
  ],
);
```

### `lib/main.dart`

```dart
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'router.dart';

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
  runApp(const MaketPeyzanApp());
}

class MaketPeyzanApp extends StatelessWidget {
  const MaketPeyzanApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Makèt Peyizan',
      debugShowCheckedModeBanner: false,
      routerConfig: router,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF2E7D32),
          primary: const Color(0xFF2E7D32),
        ),
        useMaterial3: true,
        fontFamily: 'Poppins',
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF2E7D32),
          foregroundColor: Colors.white,
          elevation: 0,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF2E7D32),
            foregroundColor: Colors.white,
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: Color(0xFF2E7D32), width: 2),
          ),
        ),
        cardTheme: CardTheme(
          elevation: 2,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      ),
    );
  }
}
```

---

## Récapitulatif des endpoints utilisés

| Écran Flutter | Méthode | Endpoint API |
|---------------|---------|--------------|
| Login | POST | `/api/auth/login/` |
| Inscription | POST | `/api/auth/register/` |
| Catalogue liste | GET | `/api/products/?page=&search=&categorie=` |
| Catégories | GET | `/api/products/categories/` |
| Détail produit | GET | `/api/products/public/<slug>/` |
| Panier | GET | `/api/orders/panier/` |
| Ajouter panier | POST | `/api/orders/panier/ajouter/` |
| Modifier quantité | PATCH | `/api/orders/panier/modifier/<slug>/` |
| Retirer article | DELETE | `/api/orders/panier/retirer/<slug>/` |
| Vider panier | DELETE | `/api/orders/panier/vider/` |
| Passer commande | POST | `/api/orders/commander/` |
| Mes commandes | GET | `/api/auth/commandes/` |
| Mes adresses | GET | `/api/auth/adresses/` |
| Créer adresse | POST | `/api/auth/adresses/` |
| Adresse défaut | POST | `/api/auth/adresses/<id>/default/` |
| Profil utilisateur | GET/PATCH | `/api/auth/me/` |
| Stats producteur | GET | `/api/auth/producteur/stats/` |
| Profil producteur | GET/PATCH | `/api/auth/producteur/profil/` |
| Commandes reçues | GET | `/api/auth/producteur/commandes/` |
| Changer statut commande | PATCH | `/api/auth/producteur/commandes/<num>/statut/` |
| Mes produits | GET | `/api/products/mes-produits/` |
| Créer produit | POST | `/api/products/mes-produits/` |
| Modifier produit | PATCH | `/api/products/mes-produits/<slug>/` |
| Supprimer produit | DELETE | `/api/products/mes-produits/<slug>/` |
| Mes participations | GET | `/api/collectes/mes-participations/` |
| Confirmer participation | PATCH | `/api/collectes/participations/<id>/confirmer/` |
| Départements | GET | `/api/geo/departements/` |
| Communes | GET | `/api/geo/communes/?dept=<slug>` |
| Sections | GET | `/api/geo/sections/?dept=<slug>&commune=<nom>` |
| Token FCM | POST | `/api/auth/fcm-token/` |
| Refresh token | POST | `/api/auth/token/refresh/` |
| Logout | POST | `/api/auth/logout/` |
